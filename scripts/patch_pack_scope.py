#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable


class ScopeError(ValueError):
    pass


def normalize_repo_path(raw: str, *, source: str) -> str:
    value = raw.strip()
    if not value:
        raise ScopeError(f"{source}: empty repository path")
    if "\\" in value:
        raise ScopeError(f"{source}: paths must use '/' separators: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ScopeError(f"{source}: unsafe repository path: {value!r}")
    normalized = path.as_posix()
    if normalized != value:
        raise ScopeError(f"{source}: path is not normalized: {value!r}")
    return normalized


def normalized_set(values: Iterable[object], *, source: str) -> set[str]:
    result: set[str] = set()
    for index, raw in enumerate(values):
        if not isinstance(raw, str):
            raise ScopeError(f"{source}[{index}]: expected string path")
        path = normalize_repo_path(raw, source=f"{source}[{index}]")
        if path in result:
            raise ScopeError(f"{source}: duplicate path: {path}")
        result.add(path)
    return result


def load_manifest(pack_root: Path) -> tuple[dict[str, object], set[str], set[str], set[str]]:
    manifest_path = pack_root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScopeError("missing manifest.json") from exc
    except json.JSONDecodeError as exc:
        raise ScopeError(f"invalid manifest.json: {exc}") from exc

    if not isinstance(manifest, dict):
        raise ScopeError("manifest.json root must be an object")

    created = normalized_set(manifest.get("files_created", []), source="files_created")
    modified = normalized_set(manifest.get("files_modified", []), source="files_modified")
    deleted = normalized_set(manifest.get("files_deleted", []), source="files_deleted")

    overlaps = {
        "created/modified": created & modified,
        "created/deleted": created & deleted,
        "modified/deleted": modified & deleted,
    }
    for label, paths in overlaps.items():
        if paths:
            raise ScopeError(f"manifest path sets overlap ({label}): {', '.join(sorted(paths))}")

    return manifest, created, modified, deleted


def strip_diff_prefix(token: str) -> str:
    if token.startswith("a/") or token.startswith("b/"):
        token = token[2:]
    return normalize_repo_path(token, source="changes.patch")


def patch_paths(path: Path) -> set[str]:
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        return set()

    result: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.startswith("diff --git "):
            continue
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            raise ScopeError(f"changes.patch:{line_number}: malformed diff header: {exc}") from exc
        if len(parts) != 4:
            raise ScopeError(f"changes.patch:{line_number}: malformed diff header")
        result.add(strip_diff_prefix(parts[2]))
        result.add(strip_diff_prefix(parts[3]))

    if not result:
        raise ScopeError("changes.patch is non-empty but contains no 'diff --git' headers")
    return result


def overlay_paths(root: Path) -> set[str]:
    if not root.is_dir():
        return set()
    result: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        result.add(normalize_repo_path(path.relative_to(root).as_posix(), source="overlay"))
    return result


def delete_paths(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    result: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        normalized = normalize_repo_path(value, source=f"delete-paths.txt:{line_number}")
        if normalized in result:
            raise ScopeError(f"delete-paths.txt:{line_number}: duplicate path: {normalized}")
        result.add(normalized)
    return result


def format_mismatch(label: str, expected: set[str], actual: set[str]) -> str:
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    details: list[str] = []
    if missing:
        details.append("missing=" + ",".join(missing))
    if extra:
        details.append("extra=" + ",".join(extra))
    return f"{label} scope mismatch: " + "; ".join(details)


def validate_pack(pack_root: Path) -> list[str]:
    errors: list[str] = []
    try:
        _manifest, created, modified, deleted = load_manifest(pack_root)
        declared_write = created | modified
        declared_all = declared_write | deleted
        patch = patch_paths(pack_root / "patch/changes.patch")
        overlay = overlay_paths(pack_root / "overlay")
        delete = delete_paths(pack_root / "patch/delete-paths.txt")

        if patch and patch != declared_write:
            errors.append(format_mismatch("changes.patch vs manifest writes", declared_write, patch))
        if overlay and overlay != declared_write:
            errors.append(format_mismatch("overlay vs manifest writes", declared_write, overlay))
        if delete != deleted:
            errors.append(format_mismatch("delete-paths.txt vs manifest deletes", deleted, delete))
        if declared_write and not patch and not overlay:
            errors.append("manifest declares created/modified files but neither changes.patch nor overlay supplies them")
        if declared_all and not patch and not overlay and not delete:
            errors.append("manifest declares repository changes but patch pack contains no implementation payload")
    except ScopeError as exc:
        errors.append(str(exc))

    deviations = pack_root / "DEVIATIONS.md"
    if not deviations.is_file():
        errors.append("missing required file: DEVIATIONS.md")

    scope_helper = pack_root / "scripts/patch_pack_scope.py"
    if not scope_helper.is_file():
        errors.append("missing required file: scripts/patch_pack_scope.py")

    return errors


def run_git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise ScopeError(f"git {' '.join(args)} failed: {message}")
    return result.stdout


def nul_paths(data: bytes, *, source: str) -> set[str]:
    result: set[str] = set()
    for raw in data.split(b"\0"):
        if not raw:
            continue
        result.add(normalize_repo_path(raw.decode("utf-8"), source=source))
    return result


def deviation_status(pack_root: Path) -> str:
    path = pack_root / "DEVIATIONS.md"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise ScopeError("missing DEVIATIONS.md") from exc
    for line in lines:
        if line.lower().startswith("status:"):
            status = line.split(":", 1)[1].strip().lower()
            if status not in {"none", "documented"}:
                raise ScopeError("DEVIATIONS.md Status must be 'none' or 'documented'")
            return status
    raise ScopeError("DEVIATIONS.md must contain 'Status: none' or 'Status: documented'")


def verify_result(pack_root: Path, repo: Path) -> list[str]:
    errors = validate_pack(pack_root)
    if errors:
        return errors

    try:
        manifest, created, modified, deleted = load_manifest(pack_root)
        target = manifest.get("target")
        if not isinstance(target, dict):
            raise ScopeError("manifest.target must be an object")
        base = str(target.get("base_revision", "")).strip()
        if not base:
            raise ScopeError("manifest.target.base_revision is required")
        run_git(repo, "rev-parse", "--verify", f"{base}^{{commit}}")

        declared = created | modified | deleted
        actual = nul_paths(run_git(repo, "diff", "--name-only", "-z", base, "--"), source="git diff")
        actual |= nul_paths(
            run_git(repo, "ls-files", "--others", "--exclude-standard", "-z"),
            source="git untracked",
        )
        if actual != declared:
            errors.append(format_mismatch("final repository diff vs manifest", declared, actual))

        check = subprocess.run(
            ["git", "-C", str(repo), "diff", "--check", base, "--"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if check.returncode != 0:
            errors.append("git diff --check failed:\n" + check.stdout.rstrip())

        deviation_status(pack_root)
    except ScopeError as exc:
        errors.append(str(exc))

    return errors


def emit(errors: list[str], *, success: str) -> int:
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {success}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Executable Patch Pack file scope.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-pack", help="Compare manifest, patch, overlay, and deletion scope.")
    validate.add_argument("pack", type=Path)

    verify = subparsers.add_parser("verify-result", help="Compare final repository diff with the manifest scope.")
    verify.add_argument("pack", type=Path)
    verify.add_argument("repository", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    pack = args.pack.resolve()
    if args.command == "validate-pack":
        return emit(validate_pack(pack), success=str(pack))
    repo = args.repository.resolve()
    return emit(verify_result(pack, repo), success=f"{repo} matches {pack / 'manifest.json'}")


if __name__ == "__main__":
    raise SystemExit(main())
