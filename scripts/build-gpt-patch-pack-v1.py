#!/usr/bin/env python3
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
import sys
import tarfile
import tempfile

RUNNER_VERSION = "1.0.0"

class BuildError(RuntimeError):
    pass

def run(argv: list[str], cwd: Path) -> str:
    proc = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode:
        raise BuildError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()

def git(repo: Path, *args: str) -> str:
    return run(["git", *args], repo)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def scope(repo: Path) -> tuple[list[str], list[str], list[str]]:
    raw = subprocess.check_output(
        ["git", "diff", "--name-status", "-z", "--find-renames", "--find-copies", "--cached", "--"],
        cwd=repo,
    )
    fields = raw.split(b"\0")
    created, modified, deleted = set(), set(), set()
    i = 0
    while i < len(fields):
        status_raw = fields[i]; i += 1
        if not status_raw:
            continue
        status = status_raw.decode("ascii")
        path = fields[i].decode("utf-8"); i += 1
        if status[0] in {"R", "C"}:
            new = fields[i].decode("utf-8"); i += 1
            if status[0] == "R":
                deleted.add(path)
            created.add(new)
        elif status[0] == "A":
            created.add(path)
        elif status[0] in {"M", "T"}:
            modified.add(path)
        elif status[0] == "D":
            deleted.add(path)
        else:
            raise BuildError(f"unsupported status: {status}")
    return sorted(created), sorted(modified), sorted(deleted)

def checksums(pack: Path) -> None:
    lines = []
    for path in sorted(p for p in pack.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        lines.append(f"{sha256(path)}  {path.relative_to(pack).as_posix()}")
    (pack/"SHA256SUMS").write_text("\n".join(lines)+"\n")

def archive(pack: Path, output: Path) -> None:
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tf:
                for path in sorted(pack.rglob("*")):
                    info = tf.gettarinfo(str(path), (Path(pack.name)/path.relative_to(pack)).as_posix())
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    if path.is_file():
                        with path.open("rb") as handle:
                            tf.addfile(info, handle)
                    else:
                        tf.addfile(info)

def main() -> int:
    parser = argparse.ArgumentParser()
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
    parser.add_argument("--output-directory", required=True, type=Path)
    parser.add_argument("--planner-commit", required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    if git(repo, "rev-parse", "HEAD") != args.base_commit:
        raise BuildError("HEAD mismatch")
    if git(repo, "branch", "--show-current") != args.branch:
        raise BuildError("branch mismatch")
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise BuildError("repository must be clean")
    if git(repo, "remote", "get-url", args.remote) not in args.accepted_origin_url:
        raise BuildError("origin mismatch")
    if git(repo, "rev-parse", args.remote_ref) != args.base_commit:
        raise BuildError("remote ref mismatch")

    requirements = json.loads(args.requirements.read_text())["requirements"]
    gates = json.loads(args.gates.read_text())["gates"]
    now = datetime.now(timezone.utc)
    patch_id = f"patch-{now:%Y%m%d-%H%M%S}-{args.slug}"
    planner = Path(__file__).resolve().parents[1]

    with tempfile.TemporaryDirectory(prefix="gpt-patch-builder-") as raw:
        temp = Path(raw)
        worktree = temp/"target"
        run(["git", "worktree", "add", "--detach", str(worktree), args.base_commit], repo)
        try:
            run(["git", "apply", "--check", "--index", "--binary", str(args.changes_patch.resolve())], worktree)
            run(["git", "apply", "--index", "--binary", str(args.changes_patch.resolve())], worktree)
            created, modified, deleted = scope(worktree)
            target_tree = git(worktree, "write-tree")
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=repo)

        pack = temp/patch_id
        (pack/"payload").mkdir(parents=True)
        shutil.copyfile(args.changes_patch, pack/"payload/changes.patch")
        shutil.copyfile(planner/"templates/gpt-patch-pack-v1/apply.py", pack/"payload/apply.py")
        os.chmod(pack/"payload/apply.py", 0o755)
        shutil.copyfile(args.agent_task, pack/"AGENT_TASK.md")
        manifest = {
            "schema_version": 2,
            "format": "gpt-patch-pack-v1",
            "patch_id": patch_id,
            "title": args.title,
            "description": args.description,
            "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "runner_version": RUNNER_VERSION,
            "baseline_release": args.baseline_release,
            "evidence_directory": f".gpt-review/evidence/{args.baseline_release}/{patch_id}",
            "workflow": {
                "repository": "https://github.com/rceman/gpt-review-planner",
                "version": "v"+(planner/"VERSION").read_text().strip(),
                "commit": args.planner_commit,
                "document": "GPT_REVIEW_PLANNER.md",
            },
            "target": {
                "repository": args.repository,
                "accepted_origin_urls": args.accepted_origin_url,
                "branch": args.branch,
                "base_revision": args.base_commit,
                "remote": args.remote,
                "remote_ref": args.remote_ref,
            },
            "payload": {
                "patch": "payload/changes.patch",
                "preflight": {"argv": ["python3","{pack}/payload/apply.py","--check","--patch","{pack}/payload/changes.patch"], "env": {}},
                "apply": {"argv": ["python3","{pack}/payload/apply.py","--apply","--patch","{pack}/payload/changes.patch"], "env": {}},
                "success_marker": "GPT_PATCH_PAYLOAD_APPLIED",
            },
            "files_created": created,
            "files_modified": modified,
            "files_deleted": deleted,
            "target_tree": target_tree,
            "requirements": requirements,
            "gates": gates,
            "compatibility": {
                "scope": "none",
                "authorized": False,
                "canonical_implementation": "GPT Patch Pack v1",
                "legacy_behavior": "unsupported and out of scope",
                "authorization_source": None,
                "supported_legacy_versions": [],
                "direction": "none",
                "removal_condition": None,
            },
            "metadata": {
                "planner_commit": args.planner_commit,
                "gpt_static_checks_performed": ["Binary patch applied in an isolated worktree and target tree recorded."],
                "gpt_runtime_checks_not_performed": ["Target runtime gates are executed by the standard runner."],
            },
        }
        (pack/"MANIFEST.json").write_text(json.dumps(manifest, indent=2)+"\n")
        checksums(pack)
        args.output_directory.mkdir(parents=True, exist_ok=True)
        output = args.output_directory/f"{patch_id}.tar.gz"
        archive(pack, output)
        digest = sha256(output)
        output.with_name(output.name+".sha256").write_text(f"{digest}  {output.name}\n")
        runner = planner/"scripts/gpt-patch-pack-runner-v1.py"
        run(["python3", str(runner), "--archive", str(output), "--archive-sha256", digest, "--repo", str(repo)], planner)
    print(f"PACK_BUILT archive={output} sha256={digest} target_tree={target_tree}")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, KeyError, json.JSONDecodeError) as exc:
        print(f"GPT_PATCH_PACK_BUILD_ABORTED: {exc}", file=sys.stderr)
        raise SystemExit(1)
