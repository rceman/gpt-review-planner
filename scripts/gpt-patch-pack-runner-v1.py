#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import selectors
import signal
import time
import re
import tarfile
import tempfile
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gpt_patch_pack_v1_common import DEFAULT_COMPATIBILITY, validate_compatibility

RUNNER_VERSION = "1.0.0"
MAX_ARCHIVE_ENTRIES = 4096
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_MEMBER_BYTES = 128 * 1024 * 1024
CANONICAL_PAYLOAD = {"patch": "payload/changes.patch", "format": "git-binary-full-index"}


class PackError(RuntimeError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PackError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def run(
    argv: list[str],
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
    timeout: int = 300,
    output_limit: int = 4 * 1024 * 1024,
) -> subprocess.CompletedProcess[str]:
    if not argv or any(not isinstance(value, str) or not value for value in argv):
        raise PackError("command argv must be a non-empty string array")
    merged = os.environ.copy()
    if env:
        merged.update(env)
    try:
        proc = subprocess.Popen(argv, cwd=cwd, env=merged, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, start_new_session=True)
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
        selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
        chunks = {"stdout": bytearray(), "stderr": bytearray()}
        total = 0
        deadline = time.monotonic() + timeout
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
                raise PackError(f"command timed out after {timeout}s: {argv!r}")
            for key, _ in selector.select(min(0.2, remaining)):
                data = key.fileobj.read1(65536)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                total += len(data)
                chunks[key.data].extend(data[-output_limit:])
                if total > output_limit:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
                    raise PackError(f"command output exceeded {output_limit} bytes: {argv!r}")
        code = proc.wait()
        stdout = bytes(chunks["stdout"]).decode(errors="replace")
        stderr = bytes(chunks["stderr"]).decode(errors="replace")
        proc = subprocess.CompletedProcess(argv, code, stdout, stderr)
    except OSError as exc:
        raise PackError(f"command execution failed: {argv!r}: {exc}") from exc
    if proc.returncode:
        raise PackError(
            f"command failed ({proc.returncode}): {argv!r}\n"
            f"stdout:\n{stdout}\nstderr:\n{stderr}"
        )
    return proc


def git(repo: Path, *args: str) -> str:
    return run(["git", *args], repo, timeout=600, output_limit=64 * 1024 * 1024).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_relative(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or any(char in value for char in ("\0", "\n", "\r"))
    ):
        raise PackError(f"{label} must be a normalized relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or "." in path.parts or ".." in path.parts or path.as_posix() != value:
        raise PackError(f"{label} is not canonical: {value!r}")
    return value


def safe_extract(archive: Path, destination: Path) -> Path:
    seen: set[str] = set()
    folded: set[str] = set()
    roots: set[str] = set()
    total = 0
    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        if not members or len(members) > MAX_ARCHIVE_ENTRIES:
            raise PackError("archive is empty or exceeds entry limit")
        for member in members:
            name = normalize_relative(member.name, "archive member")
            if name in seen or name.casefold() in folded:
                raise PackError(f"duplicate or case-folding archive member: {name}")
            seen.add(name)
            folded.add(name.casefold())
            roots.add(PurePosixPath(name).parts[0])
            if member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
                raise PackError(f"archive member type is forbidden: {name}")
            if member.size < 0 or member.size > MAX_MEMBER_BYTES:
                raise PackError(f"archive member size is invalid: {name}")
            total += member.size
            if total > MAX_ARCHIVE_BYTES:
                raise PackError("archive expanded-size limit exceeded")
            if member.isfile() and stat.S_IMODE(member.mode) != 0o644:
                raise PackError(f"archive mode is forbidden: {name}")
            if member.isdir() and stat.S_IMODE(member.mode) != 0o755:
                raise PackError(f"archive directory mode is forbidden: {name}")
        if len(roots) != 1:
            raise PackError(f"archive must contain one root: {sorted(roots)}")
        tf.extractall(destination, filter="data")
    root = destination / next(iter(roots))
    if not root.is_dir() or root.is_symlink():
        raise PackError("archive root is invalid")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*")}
    expected = {"MANIFEST.json", "SHA256SUMS", "AGENT_TASK.md", "payload", "payload/changes.patch"}
    if actual != expected:
        raise PackError(f"archive member set invalid: {sorted(actual)}")
    return root


def verify_checksums(pack: Path) -> None:
    sums = pack / "SHA256SUMS"
    if not sums.is_file() or sums.is_symlink():
        raise PackError("SHA256SUMS missing")
    declared: dict[str, str] = {}
    for number, line in enumerate(sums.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise PackError(f"invalid SHA256SUMS line {number}")
        expected, raw = parts
        relative = normalize_relative(raw.lstrip(" *"), "SHA256SUMS path")
        if relative == "SHA256SUMS" or relative in declared:
            raise PackError(f"invalid or duplicate checksum path: {relative}")
        if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise PackError(f"invalid SHA-256: {relative}")
        target = pack / relative
        if not target.is_file() or target.is_symlink():
            raise PackError(f"checksummed file missing: {relative}")
        if sha256(target) != expected:
            raise PackError(f"checksum mismatch: {relative}")
        declared[relative] = expected
    actual = {
        path.relative_to(pack).as_posix()
        for path in pack.rglob("*")
        if path.is_file() and not path.is_symlink() and path.name != "SHA256SUMS"
    }
    if actual != set(declared):
        raise PackError(
            f"checksum coverage mismatch: missing={sorted(actual-set(declared))} "
            f"extra={sorted(set(declared)-actual)}"
        )


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PackError(f"JSON root must be an object: {path}")
    return value


def exact_keys(value: dict[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise PackError(
            f"{label} keys invalid; missing={sorted(keys-set(value))} "
            f"unknown={sorted(set(value)-keys)}"
        )


def validate_command(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PackError(f"{label} must be an object")
    exact_keys(value, {"argv", "env"}, label)
    argv, env = value["argv"], value["env"]
    if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x for x in argv):
        raise PackError(f"{label}.argv invalid")
    if not isinstance(env, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in env.items()):
        raise PackError(f"{label}.env invalid")
    return value


def validate_manifest(pack: Path) -> dict[str, Any]:
    task = pack / "AGENT_TASK.md"
    if not task.is_file() or task.is_symlink():
        raise PackError("AGENT_TASK.md missing or not regular")
    try:
        task.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PackError("AGENT_TASK.md is not valid UTF-8") from exc
    value = load_json(pack / "MANIFEST.json")
    required = {
        "schema_version", "format", "patch_id", "title", "description",
        "created_at", "runner_version", "baseline_release",
        "evidence_directory", "workflow", "target", "payload",
        "files_created", "files_modified", "files_deleted", "target_tree",
        "requirements", "gates", "compatibility", "metadata",
    }
    exact_keys(value, required, "manifest")
    if value["schema_version"] != 2 or value["format"] != "gpt-patch-pack-v1":
        raise PackError("unsupported manifest format")
    if value["runner_version"] != RUNNER_VERSION:
        raise PackError("runner version mismatch")
    if not isinstance(value["patch_id"], str) or not re.fullmatch(r"patch-[0-9]{8}-[0-9]{6}-[a-z0-9][a-z0-9-]{0,63}", value["patch_id"]):
        raise PackError("invalid patch_id")
    if value["evidence_directory"] != f".gpt-review/evidence/{value['baseline_release']}/{value['patch_id']}":
        raise PackError("evidence directory identity mismatch")

    workflow = value["workflow"]
    if not isinstance(workflow, dict):
        raise PackError("workflow must be an object")
    exact_keys(workflow, {"repository", "version", "commit", "document"}, "workflow")
    if workflow["repository"] != "https://github.com/rceman/gpt-review-planner" or workflow["document"] != "GPT_REVIEW_PLANNER.md":
        raise PackError("workflow identity mismatch")

    target = value["target"]
    if not isinstance(target, dict):
        raise PackError("target must be an object")
    exact_keys(
        target,
        {"repository", "accepted_origin_urls", "branch", "base_revision", "remote", "remote_ref"},
        "target",
    )
    if not isinstance(target["accepted_origin_urls"], list) or not target["accepted_origin_urls"]:
        raise PackError("accepted_origin_urls invalid")
    if not isinstance(target["base_revision"], str) or len(target["base_revision"]) != 40:
        raise PackError("base_revision invalid")

    payload = value["payload"]
    if not isinstance(payload, dict):
        raise PackError("payload must be an object")
    exact_keys(payload, {"patch", "format"}, "payload")
    if payload != CANONICAL_PAYLOAD:
        raise PackError("payload patch path is not canonical")
    if not (pack / "payload/changes.patch").is_file():
        raise PackError("payload patch missing")

    classes = []
    for key in ("files_created", "files_modified", "files_deleted"):
        raw = value[key]
        if not isinstance(raw, list) or any(not isinstance(x, str) for x in raw):
            raise PackError(f"{key} must be a string array")
        normalized = [normalize_relative(x, key) for x in raw]
        if len(normalized) != len(set(normalized)):
            raise PackError(f"{key} contains duplicates")
        classes.append(set(normalized))
    if classes[0] & classes[1] or classes[0] & classes[2] or classes[1] & classes[2]:
        raise PackError("file operation classes overlap")

    tree = value["target_tree"]
    if not isinstance(tree, str) or len(tree) != 40 or any(c not in "0123456789abcdef" for c in tree):
        raise PackError("target_tree invalid")

    requirements = value["requirements"]
    if not isinstance(requirements, list) or not requirements:
        raise PackError("requirements must be non-empty")
    requirement_ids = []
    for item in requirements:
        if not isinstance(item, dict):
            raise PackError("requirement must be an object")
        exact_keys(item, {"id", "summary", "acceptance"}, "requirement")
        if not isinstance(item["id"], str) or not item["id"]:
            raise PackError("requirement id invalid")
        requirement_ids.append(item["id"])
    if len(requirement_ids) != len(set(requirement_ids)):
        raise PackError("duplicate requirement ID")

    gates = value["gates"]
    if not isinstance(gates, list) or not gates:
        raise PackError("gates must be non-empty")
    gate_ids = []
    for gate in gates:
        if not isinstance(gate, dict):
            raise PackError("gate must be an object")
        exact_keys(
            gate,
            {"id", "name", "kind", "argv", "env", "timeout_seconds", "max_output_bytes"},
            "gate",
        )
        if gate["kind"] != "command":
            raise PackError("only command gates are supported")
        validate_command({"argv": gate["argv"], "env": gate["env"]}, "gate")
        if not isinstance(gate["timeout_seconds"], int) or not 1 <= gate["timeout_seconds"] <= 7200:
            raise PackError("gate timeout invalid")
        if not isinstance(gate["max_output_bytes"], int) or not 1024 <= gate["max_output_bytes"] <= 16777216:
            raise PackError("gate output limit invalid")
        gate_ids.append(gate["id"])
    if len(gate_ids) != len(set(gate_ids)):
        raise PackError("duplicate gate ID")

    compatibility = value["compatibility"]
    try:
        validate_compatibility(compatibility)
    except ValueError as exc:
        raise PackError(str(exc)) from exc

    metadata = value["metadata"]
    if not isinstance(metadata, dict):
        raise PackError("metadata must be an object")
    exact_keys(
        metadata,
        {"planner_commit", "gpt_static_checks_performed", "gpt_runtime_checks_not_performed"},
        "metadata",
    )
    return value


def expand(argv: list[str], pack: Path) -> list[str]:
    return [value.replace("{pack}", str(pack)) for value in argv]


def execute(command: dict[str, Any], repo: Path, pack: Path, marker: str | None = None) -> str:
    proc = run(expand(command["argv"], pack), repo, env=command["env"])
    output = (proc.stdout or "") + (proc.stderr or "")
    if marker and marker not in output:
        raise PackError(f"success marker missing: {marker}")
    return output


def run_gates(gates: list[dict[str, Any]], repo: Path, pack: Path) -> None:
    for gate in gates:
        print(f"GATE_START {gate['id']}", flush=True)
        run(
            expand(gate["argv"], pack),
            repo,
            env=gate["env"],
            timeout=gate["timeout_seconds"],
            output_limit=gate["max_output_bytes"],
        )
        print(f"GATE_OK {gate['id']}", flush=True)


def parse_scope(repo: Path) -> tuple[set[str], set[str], set[str]]:
    raw = subprocess.check_output(
        ["git", "diff", "--name-status", "-z", "--find-renames", "--find-copies", "--cached", "--"],
        cwd=repo,
    )
    fields = raw.split(b"\0")
    created: set[str] = set()
    modified: set[str] = set()
    deleted: set[str] = set()
    i = 0
    while i < len(fields):
        status_raw = fields[i]
        i += 1
        if not status_raw:
            continue
        status = status_raw.decode("ascii")
        code = status[0]
        path = normalize_relative(fields[i].decode("utf-8"), "git path")
        i += 1
        if code in {"R", "C"}:
            new = normalize_relative(fields[i].decode("utf-8"), "git destination")
            i += 1
            if code == "R":
                deleted.add(path)
            created.add(new)
        elif code == "A":
            created.add(path)
        elif code in {"M", "T"}:
            modified.add(path)
        elif code == "D":
            deleted.add(path)
        else:
            raise PackError(f"unsupported Git status: {status}")
    return created, modified, deleted


def verify_scope(repo: Path, manifest: dict[str, Any]) -> None:
    expected = (
        set(manifest["files_created"]),
        set(manifest["files_modified"]),
        set(manifest["files_deleted"]),
    )
    actual = parse_scope(repo)
    if actual != expected:
        raise PackError(
            f"scope mismatch expected={tuple(sorted(x) for x in expected)} "
            f"actual={tuple(sorted(x) for x in actual)}"
        )


def verify_repo(repo: Path, manifest: dict[str, Any]) -> None:
    target = manifest["target"]
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise PackError("--repo must identify the worktree root")
    origin = git(repo, "remote", "get-url", target["remote"])
    if origin not in target["accepted_origin_urls"]:
        raise PackError(f"unexpected origin: {origin}")
    if git(repo, "branch", "--show-current") != target["branch"]:
        raise PackError("wrong branch")
    if git(repo, "rev-parse", "HEAD") != target["base_revision"]:
        raise PackError("wrong local HEAD")
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise PackError("real worktree must be clean")
    run(["git", "fetch", target["remote"], "--prune", "--tags"], repo, timeout=600)
    if git(repo, "rev-parse", target["remote_ref"]) != target["base_revision"]:
        raise PackError("remote ref moved")


def worktree_add(repo: Path, path: Path, base: str) -> None:
    run(["git", "worktree", "add", "--detach", str(path), base], repo)


def worktree_remove(repo: Path, path: Path) -> None:
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(path)],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    shutil.rmtree(path, ignore_errors=True)


def staged_tree(repo: Path) -> str:
    run(["git", "add", "-A"], repo)
    return git(repo, "write-tree")


def restore_real(repo: Path, base: str, created: list[str]) -> None:
    subprocess.run(["git", "reset", "--hard", base], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for relative in sorted(created, key=lambda x: len(PurePosixPath(x).parts), reverse=True):
        target = repo.joinpath(*PurePosixPath(normalize_relative(relative, "rollback path")).parts)
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
    if git(repo, "rev-parse", "HEAD") != base or git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise PackError("rollback did not restore exact clean base")


def main() -> int:
    parser = argparse.ArgumentParser(description="GPT Patch Pack v1 runner")
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    archive = args.archive.resolve()
    repo = args.repo.resolve()
    if not archive.is_file() or sha256(archive) != args.archive_sha256:
        raise PackError("outer archive SHA-256 mismatch")

    with tempfile.TemporaryDirectory(prefix="gpt-patch-pack-v1-") as raw:
        temp = Path(raw)
        pack = safe_extract(archive, temp / "pack")
        verify_checksums(pack)
        manifest = validate_manifest(pack)
        planner = Path(__file__).resolve().parents[1]
        planner_commit = git(planner, "rev-parse", "HEAD")
        if manifest["workflow"]["commit"] != planner_commit or manifest["metadata"]["planner_commit"] != planner_commit:
            raise PackError("planner commit pin mismatch")
        if manifest["workflow"]["version"] != "v" + (planner / "VERSION").read_text(encoding="utf-8").strip():
            raise PackError("planner version pin mismatch")
        verify_repo(repo, manifest)
        base = manifest["target"]["base_revision"]
        first = temp / "worktree-a"
        second = temp / "worktree-b"
        verified_patch = temp / "verified.patch"
        try:
            worktree_add(repo, first, base)
            before = git(first, "status", "--porcelain=v1", "--untracked-files=all")
            if before:
                raise PackError("worktree A is not clean")
            run(["git", "apply", "--check", "--index", "--binary", str(pack / "payload/changes.patch")], first)
            run(["git", "apply", "--index", "--binary", str(pack / "payload/changes.patch")], first)
            if git(first, "rev-parse", "HEAD") != base:
                raise PackError("payload changed HEAD")
            run_gates(manifest["gates"], first, pack)
            tree = staged_tree(first)
            verify_scope(first, manifest)
            if tree != manifest["target_tree"]:
                raise PackError("worktree A target tree mismatch")
            patch_text = run(
                ["git", "diff", "--cached", "--binary", "--full-index", "HEAD", "--"],
                first,
                output_limit=64 * 1024 * 1024,
            ).stdout
            if not patch_text:
                raise PackError("verified patch is empty")
            verified_patch.write_text(patch_text, encoding="utf-8")

            worktree_add(repo, second, base)
            run(["git", "apply", "--check", "--index", "--binary", str(verified_patch)], second)
            run(["git", "apply", "--index", "--binary", str(verified_patch)], second)
            if git(second, "write-tree") != tree:
                raise PackError("worktree B target tree mismatch")
            verify_scope(second, manifest)
            run_gates(manifest["gates"], second, pack)
            if staged_tree(second) != tree:
                raise PackError("gates changed worktree B tree")

            print(f"PACK_VERIFIED pack_id={manifest['patch_id']} target_tree={tree}")
            if not args.apply:
                print("REAL_WORKTREE_UNCHANGED")
                return 0

            if git(repo, "rev-parse", "HEAD") != base or git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
                raise PackError("real checkout changed during isolated validation")
            try:
                run(["git", "apply", "--check", "--index", "--binary", str(verified_patch)], repo)
                run(["git", "apply", "--index", "--binary", str(verified_patch)], repo)
                if git(repo, "write-tree") != tree:
                    raise PackError("real target tree mismatch")
                verify_scope(repo, manifest)
                run(["git", "reset"], repo)
            except Exception:
                restore_real(repo, base, manifest["files_created"])
                raise
            print(f"GPT_PATCH_PACK_APPLIED pack_id={manifest['patch_id']} target_tree={tree}")
            return 0
        finally:
            worktree_remove(repo, first)
            worktree_remove(repo, second)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PackError as exc:
        print(f"GPT_PATCH_PACK_ABORTED: {exc}", file=sys.stderr)
        raise SystemExit(1)
