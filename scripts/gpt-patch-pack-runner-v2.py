#!/usr/bin/env python3
"""Verify and, only when requested, apply a data-only GPT Patch Pack v2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tarfile
import tempfile

from gpt_patch_pack_common import load_json, sha256, validate_manifest


class PackError(RuntimeError):
    pass


EXPECTED = {"MANIFEST.json", "SHA256SUMS", "AGENT_TASK.md", "payload", "payload/changes.patch"}


def safe_member_name(name: str) -> str:
    if not name or "\\" in name or name.startswith("/") or ":" in name.split("/")[0]:
        raise PackError(f"unsafe archive member: {name!r}")
    p = PurePosixPath(name)
    if p.is_absolute() or "." in p.parts or ".." in p.parts:
        raise PackError(f"unsafe archive member: {name!r}")
    return p.as_posix()


def extract_archive(archive: Path, destination: Path) -> Path:
    try:
        tf = tarfile.open(archive, "r:gz")
    except (OSError, tarfile.TarError) as exc:
        raise PackError(f"invalid archive: {exc}") from exc
    with tf:
        members = tf.getmembers()
        if not members:
            raise PackError("archive is empty")
        roots: set[str] = set(); seen: set[str] = set(); folded: set[str] = set(); total = 0
        for member in members:
            name = safe_member_name(member.name)
            root = name.split("/", 1)[0]
            roots.add(root)
            relative = name.split("/", 1)[1] if "/" in name else ""
            if relative in seen:
                raise PackError(f"duplicate archive member: {name}")
            seen.add(relative)
            folded_name = relative.casefold()
            if folded_name in folded:
                raise PackError(f"case-folding archive collision: {name}")
            folded.add(folded_name)
            if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                raise PackError(f"archive member type is forbidden: {name}")
            if member.isfile() and stat.S_IMODE(member.mode) != 0o644:
                raise PackError(f"archive file mode is forbidden: {name}")
            if member.isdir() and stat.S_IMODE(member.mode) != 0o755:
                raise PackError(f"archive directory mode is forbidden: {name}")
            if member.isfile():
                total += member.size
                if member.size > 64 * 1024 * 1024 or total > 128 * 1024 * 1024:
                    raise PackError("archive expanded-size limit exceeded")
        if len(roots) != 1:
            raise PackError("archive must contain exactly one root")
        root_name = next(iter(roots))
        actual = {item for item in seen if item}
        if actual != EXPECTED:
            raise PackError(f"archive member set invalid: {sorted(actual)}")
        root = destination / root_name
        root.mkdir(parents=True)
        for member in members:
            name = safe_member_name(member.name)
            if name == root_name:
                continue
            target = destination / name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=False)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                source = tf.extractfile(member)
                if source is None:
                    raise PackError(f"cannot read archive member: {name}")
                with target.open("xb") as handle:
                    shutil.copyfileobj(source, handle)
        return root


def verify_checksums(pack: Path) -> None:
    sums = pack / "SHA256SUMS"
    try:
        lines = sums.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise PackError("SHA256SUMS is missing or invalid UTF-8") from exc
    declared: dict[str, str] = {}
    for number, line in enumerate(lines, 1):
        fields = line.split()
        if len(fields) != 2 or len(fields[0]) != 64 or any(ch not in "0123456789abcdef" for ch in fields[0]):
            raise PackError(f"malformed checksum entry {number}")
        relative = safe_member_name(fields[1])
        if relative in {"SHA256SUMS", ""} or relative in declared:
            raise PackError(f"duplicate or forbidden checksum path: {relative}")
        path = pack / relative
        if not path.is_file() or path.is_symlink() or sha256(path) != fields[0]:
            raise PackError(f"checksum mismatch: {relative}")
        declared[relative] = fields[0]
    actual = {item.relative_to(pack).as_posix() for item in pack.rglob("*") if item.is_file() and not item.is_symlink() and item.name != "SHA256SUMS"}
    if set(declared) != actual:
        raise PackError(f"checksum coverage mismatch: missing={sorted(actual-set(declared))} extra={sorted(set(declared)-actual)}")


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        raise PackError(result.stderr.strip() or result.stdout.strip() or "git command failed")
    return result.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    archive = args.archive.resolve(); repo = args.repo.resolve()
    if not archive.is_file() or sha256(archive) != args.archive_sha256:
        raise PackError("outer archive SHA-256 mismatch")
    with tempfile.TemporaryDirectory(prefix="gpt-patch-v2-runner-") as raw:
        root = extract_archive(archive, Path(raw))
        verify_checksums(root)
        manifest = load_json(root / "MANIFEST.json")
        try:
            validate_manifest(manifest, pack_root=root)
        except ValueError as exc:
            raise PackError(str(exc)) from exc
        target = manifest["target"]
        if git(repo, "rev-parse", "HEAD") != target["base_revision"]:
            raise PackError("target HEAD does not match manifest base_revision")
        if git(repo, "branch", "--show-current") != target["branch"]:
            raise PackError("target branch does not match manifest")
        if git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
            raise PackError("target repository must be clean")
        if not args.apply:
            print(f"GPT_PATCH_PACK_V2_VERIFIED mode={manifest['execution_mode']} patch_id={manifest['patch_id']}")
            return 0
        patch = root / "payload/changes.patch"
        subprocess.run(["git", "-C", str(repo), "apply", "--check", "--index", "--binary", str(patch)], check=True)
        subprocess.run(["git", "-C", str(repo), "apply", "--index", "--binary", str(patch)], check=True)
        tree = git(repo, "write-tree")
        if tree != manifest["target_tree"]:
            subprocess.run(["git", "-C", str(repo), "reset", "--mixed", "HEAD"], check=False)
            raise PackError("applied target tree does not match manifest")
        subprocess.run(["git", "-C", str(repo), "reset", "--mixed", "HEAD"], check=True, stdout=subprocess.DEVNULL)
        print(f"GPT_PATCH_PACK_V2_APPLIED mode={manifest['execution_mode']} patch_id={manifest['patch_id']} target_tree={tree}")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PackError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"GPT_PATCH_PACK_V2_REJECTED: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1)
