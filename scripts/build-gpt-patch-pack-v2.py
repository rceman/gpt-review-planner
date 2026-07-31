#!/usr/bin/env python3
"""Build the one canonical data-only GPT Patch Pack v2 archive."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

from gpt_patch_pack_common import DEFAULT_COMPATIBILITY, load_json, sha256, validate_compatibility, validate_manifest


class BuildError(RuntimeError):
    pass


def run(argv: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> str:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    result = subprocess.run(argv, cwd=cwd, env=merged, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise BuildError(result.stderr.strip() or result.stdout.strip() or "command failed")
    return result.stdout.strip()


def git(repo: Path, *args: str) -> str:
    return run(["git", *args], repo)


def scope(repo: Path) -> tuple[list[str], list[str], list[str]]:
    raw = subprocess.check_output(["git", "diff", "--name-status", "-z", "--find-renames", "--find-copies", "--cached", "--"], cwd=repo)
    tokens = raw.split(b"\0")
    created: set[str] = set(); modified: set[str] = set(); deleted: set[str] = set(); index = 0
    while index < len(tokens) - 1:
        status_token = tokens[index]; index += 1
        if not status_token:
            continue
        try:
            status = status_token.decode("ascii")
            first = tokens[index].decode("utf-8"); index += 1
        except UnicodeDecodeError as exc:
            raise BuildError("malformed UTF-8 scope record") from exc
        if status[0] in {"R", "C"}:
            if index >= len(tokens) or not tokens[index]:
                raise BuildError("truncated rename/copy scope record")
            second = tokens[index].decode("utf-8"); index += 1
            if status[0] == "R":
                deleted.add(first)
            created.add(second)
        elif status[0] == "A": created.add(first)
        elif status[0] in {"M", "T"}: modified.add(first)
        elif status[0] == "D": deleted.add(first)
        else: raise BuildError(f"unsupported scope status: {status}")
    if index != len(tokens) - 1:
        raise BuildError("malformed scope records")
    return sorted(created), sorted(modified), sorted(deleted)


def write_checksums(pack: Path) -> None:
    files = [pack / item for item in ("AGENT_TASK.md", "MANIFEST.json", "payload/changes.patch")]
    (pack / "SHA256SUMS").write_text("".join(f"{sha256(path)}  {path.relative_to(pack).as_posix()}\n" for path in files), encoding="utf-8")


def make_archive(pack: Path, output: Path, epoch: int) -> None:
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=epoch) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as archive:
                members = [pack] + sorted(pack.rglob("*"), key=lambda item: item.relative_to(pack).as_posix())
                for path in members:
                    name = (Path(pack.name) if path == pack else Path(pack.name) / path.relative_to(pack)).as_posix()
                    info = archive.gettarinfo(str(path), name)
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = epoch
                    info.mode = 0o755 if path.is_dir() else 0o644
                    if path.is_file():
                        with path.open("rb") as handle:
                            archive.addfile(info, handle)
                    else:
                        archive.addfile(info)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--accepted-origin-url", required=True, action="append")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--remote-ref", required=True)
    parser.add_argument("--baseline-release", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--changes-patch", required=True, type=Path)
    parser.add_argument("--agent-task", required=True, type=Path)
    parser.add_argument("--requirements", required=True, type=Path)
    parser.add_argument("--gates", required=True, type=Path)
    parser.add_argument("--execution-mode", required=True, choices=("gpt_tunnel_managed", "repository_evidence"))
    parser.add_argument("--output-directory", required=True, type=Path)
    parser.add_argument("--compatibility-declaration", type=Path)
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    if git(repo, "rev-parse", "HEAD") != args.base_commit or git(repo, "branch", "--show-current") != args.branch:
        raise BuildError("target repository identity mismatch")
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise BuildError("target repository must be clean")
    if git(repo, "remote", "get-url", args.remote) not in args.accepted_origin_url or git(repo, "rev-parse", args.remote_ref) != args.base_commit:
        raise BuildError("target remote identity mismatch")
    planner = Path(__file__).resolve().parents[1]
    planner_commit = git(planner, "rev-parse", "HEAD")
    if git(planner, "status", "--porcelain=v1", "--untracked-files=all") and os.environ.get("GPT_PATCH_PACK_SOURCE_COMPLETE") != "1":
        raise BuildError("planner checkout must be clean")
    if args.compatibility_declaration:
        compatibility = load_json(args.compatibility_declaration)
        validate_compatibility(compatibility)
    else:
        compatibility = dict(DEFAULT_COMPATIBILITY)
    requirements = load_json(args.requirements)["requirements"]
    gates = load_json(args.gates)["gates"]
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))
    now = datetime.fromtimestamp(epoch, timezone.utc)
    patch_id = f"patch-{now:%Y%m%d-%H%M%S}-{args.slug}"
    with tempfile.TemporaryDirectory(prefix="gpt-patch-v2-") as raw:
        temp = Path(raw)
        target = temp / "target"
        run(["git", "worktree", "add", "--detach", str(target), args.base_commit], repo)
        try:
            run(["git", "apply", "--check", "--index", "--binary", str(args.changes_patch.resolve())], target)
            run(["git", "apply", "--index", "--binary", str(args.changes_patch.resolve())], target)
            created, modified, deleted = scope(target)
            target_tree = git(target, "write-tree")
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(target)], cwd=repo, check=False)
        pack = temp / patch_id
        (pack / "payload").mkdir(parents=True)
        shutil.copyfile(args.changes_patch, pack / "payload/changes.patch")
        shutil.copyfile(args.agent_task, pack / "AGENT_TASK.md")
        manifest: dict[str, object] = {
            "schema_version": 2, "format": "gpt-patch-pack-v2", "patch_id": patch_id,
            "title": args.title, "description": args.description, "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "runner_version": "2.0.0", "baseline_release": args.baseline_release,
            "execution_mode": args.execution_mode,
            "workflow": {"repository": "https://github.com/rceman/gpt-review-planner", "version": "v" + (planner / "VERSION").read_text().strip(), "commit": planner_commit, "document": "GPT_REVIEW_PLANNER.md"},
            "target": {"repository": args.repository, "accepted_origin_urls": args.accepted_origin_url, "branch": args.branch, "base_revision": args.base_commit, "remote": args.remote, "remote_ref": args.remote_ref},
            "payload": {"patch": "payload/changes.patch", "format": "git-binary-full-index"},
            "files_created": created, "files_modified": modified, "files_deleted": deleted, "target_tree": target_tree,
            "requirements": requirements, "gates": gates, "compatibility": compatibility,
            "metadata": {"planner_commit": planner_commit, "gpt_static_checks_performed": ["Isolated binary patch application and exact target tree verification."], "gpt_runtime_checks_not_performed": ["Runtime gates are executed by the local agent or tunnel workflow."]},
        }
        if args.execution_mode == "repository_evidence":
            manifest["evidence_directory"] = f".gpt-review/evidence/{args.baseline_release}/{patch_id}"
        (pack / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        validate_manifest(manifest)
        write_checksums(pack)
        validate_manifest(manifest, pack_root=pack)
        args.output_directory.mkdir(parents=True, exist_ok=True)
        output = args.output_directory / f"{patch_id}.tar.gz"
        make_archive(pack, output, epoch)
        digest = sha256(output)
        output.with_name(output.name + ".sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(f"PACK_BUILT archive={output} sha256={digest} mode={args.execution_mode} target_tree={target_tree}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, KeyError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"GPT_PATCH_PACK_V2_BUILD_ABORTED: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1)
