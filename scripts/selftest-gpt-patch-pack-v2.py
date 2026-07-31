#!/usr/bin/env python3
"""Deterministic synthetic smoke test for the v2 data-only pack path."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def run(argv: list[str], cwd: Path) -> str:
    result = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout.strip()


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="gpt-pack-v2-selftest-") as raw:
        root = Path(raw); remote = root / "remote.git"; repo = root / "repo"; author = root / "author"; out1 = root / "out1"; out2 = root / "out2"
        run(["git", "init", "--bare", str(remote)], root)
        run(["git", "clone", str(remote), str(repo)], root)
        run(["git", "config", "user.name", "selftest"], repo); run(["git", "config", "user.email", "selftest@example.invalid"], repo); run(["git", "switch", "-c", "main"], repo)
        (repo / "README.md").write_text("before\n", encoding="utf-8"); run(["git", "add", "--all"], repo); run(["git", "commit", "-m", "base"], repo); run(["git", "push", "-u", "origin", "main"], repo)
        base = run(["git", "rev-parse", "HEAD"], repo)
        run(["git", "clone", "--branch", "main", str(remote), str(author)], root)
        run(["git", "config", "user.name", "selftest"], author); run(["git", "config", "user.email", "selftest@example.invalid"], author)
        (author / "README.md").write_text("after\n", encoding="utf-8"); (author / "new.txt").write_text("new\n", encoding="utf-8"); run(["git", "add", "--all"], author)
        patch = root / "changes.patch"; patch.write_bytes(subprocess.check_output(["git", "diff", "--cached", "--binary", "--full-index", "HEAD", "--"], cwd=author))
        task = root / "AGENT_TASK.md"; task.write_text("# AGENT_TASK\n", encoding="utf-8")
        requirements = root / "requirements.json"; requirements.write_text(json.dumps({"requirements": [{"id": "REQ-001", "summary": "Exact tree", "acceptance": ["The target tree is exact."]}]}), encoding="utf-8")
        gates = root / "gates.json"; gates.write_text(json.dumps({"gates": [{"id": "G1", "name": "Compile", "kind": "command", "argv": ["python3", "-m", "compileall", "-q", "scripts"], "env": {}, "timeout_seconds": 60, "max_output_bytes": 1048576}]}), encoding="utf-8")
        env = {"SOURCE_DATE_EPOCH": "1751241600", "GPT_PATCH_PACK_SOURCE_COMPLETE": "1"}
        build_args = ["python3", str(ROOT / "scripts/build-gpt-patch-pack-v2.py"), "--repo", str(repo), "--repository", "selftest/repo", "--accepted-origin-url", str(remote), "--branch", "main", "--base-commit", base, "--remote", "origin", "--remote-ref", "refs/remotes/origin/main", "--baseline-release", "v2.0.0", "--slug", "synthetic", "--title", "Synthetic", "--description", "Synthetic v2", "--changes-patch", str(patch), "--agent-task", str(task), "--requirements", str(requirements), "--gates", str(gates), "--execution-mode", "gpt_tunnel_managed"]
        for output in (out1, out2):
            result = subprocess.run(build_args + ["--output-directory", str(output)], cwd=ROOT, env={**__import__('os').environ, **env}, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode:
                raise RuntimeError(result.stderr or result.stdout)
        archive = next(out1.glob("*.tar.gz")); second = next(out2.glob("*.tar.gz"))
        if archive.read_bytes() != second.read_bytes():
            raise RuntimeError("controlled builds are not byte-identical")
        if archive.with_name(archive.name + ".sha256").read_bytes() != second.with_name(second.name + ".sha256").read_bytes():
            raise RuntimeError("controlled sidecars are not byte-identical")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        verify = subprocess.run(["python3", str(ROOT / "scripts/gpt-patch-pack-runner-v2.py"), "--archive", str(archive), "--archive-sha256", digest, "--repo", str(repo)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if verify.returncode or "VERIFIED" not in verify.stdout:
            raise RuntimeError(verify.stderr or verify.stdout)
        if run(["git", "status", "--porcelain=v1", "--untracked-files=all"], repo):
            raise RuntimeError("verify-only changed the target repository")
        print(f"GPT_PATCH_PACK_V2_SELFTEST_OK archive_sha256={digest}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"GPT_PATCH_PACK_V2_SELFTEST_FAILED: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1)
