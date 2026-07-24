#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


class ReleaseError(RuntimeError):
    pass


@dataclass(frozen=True)
class VersionFile:
    path: str
    kind: str
    optional: bool = False
    pointer: str | None = None
    table: str | None = None
    key: str | None = None


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise ReleaseError(message)
    return result


def repository_root(value: str | None) -> Path:
    if value:
        root = Path(value).resolve()
    else:
        root = Path(__file__).resolve().parents[1]
    if not (root / ".git").exists():
        raise ReleaseError(f"not a Git repository root: {root}")
    return root


def load_config(repo: Path, config_name: str) -> dict[str, Any]:
    path = repo / config_name
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReleaseError(f"missing release config: {config_name}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"invalid release config JSON: {exc}") from exc
    if data.get("schema_version") != 1:
        raise ReleaseError("release config schema_version must be 1")
    if not isinstance(data.get("version_files"), list) or not data["version_files"]:
        raise ReleaseError("release config version_files must be a non-empty list")
    return data


def parse_version_files(config: dict[str, Any]) -> list[VersionFile]:
    result: list[VersionFile] = []
    for index, raw in enumerate(config["version_files"], 1):
        if not isinstance(raw, dict):
            raise ReleaseError(f"version_files[{index}] must be an object")
        path = raw.get("path")
        kind = raw.get("kind")
        if not isinstance(path, str) or not path:
            raise ReleaseError(f"version_files[{index}].path must be a non-empty string")
        if kind not in {"plain", "json", "toml"}:
            raise ReleaseError(f"unsupported version file kind for {path}: {kind!r}")
        result.append(
            VersionFile(
                path=path,
                kind=kind,
                optional=bool(raw.get("optional", False)),
                pointer=raw.get("pointer"),
                table=raw.get("table"),
                key=raw.get("key"),
            )
        )
    paths = [entry.path for entry in result]
    if len(paths) != len(set(paths)):
        raise ReleaseError("release config contains duplicate version file paths")
    return result


def validate_semver(version: str) -> str:
    if not SEMVER_RE.fullmatch(version):
        raise ReleaseError(f"invalid semantic version: {version!r}")
    return version


def json_pointer_parts(pointer: str | None, path: str) -> list[str]:
    if not pointer or not pointer.startswith("/"):
        raise ReleaseError(f"JSON version file {path} requires an absolute pointer")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def read_json_pointer(data: Any, parts: Iterable[str], path: str) -> Any:
    current = data
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            raise ReleaseError(f"JSON pointer not found in {path}: /{'/'.join(parts)}")
        current = current[part]
    return current


def write_json_pointer(data: Any, parts: list[str], value: str, path: str) -> None:
    current = data
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            raise ReleaseError(f"JSON pointer not found in {path}: /{'/'.join(parts)}")
        current = current[part]
    if not parts or not isinstance(current, dict) or parts[-1] not in current:
        raise ReleaseError(f"JSON pointer not found in {path}: /{'/'.join(parts)}")
    current[parts[-1]] = value


def toml_version_location(text: str, entry: VersionFile) -> tuple[list[str], int, re.Match[str]]:
    if not entry.table or not entry.key:
        raise ReleaseError(f"TOML version file {entry.path} requires table and key")
    table_pattern = re.compile(r"^\s*\[([^\]]+)\]\s*(?:#.*)?$")
    key_pattern = re.compile(
        rf'^(\s*{re.escape(entry.key)}\s*=\s*")([^"]+)("[^\r\n]*)(\r?\n)?$'
    )
    lines = text.splitlines(keepends=True)
    current_table: str | None = None
    matches: list[tuple[int, re.Match[str]]] = []
    for index, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        table_match = table_pattern.fullmatch(stripped)
        if table_match:
            current_table = table_match.group(1).strip()
            continue
        if current_table == entry.table:
            key_match = key_pattern.fullmatch(line)
            if key_match:
                matches.append((index, key_match))
    if not matches:
        raise ReleaseError(f"TOML version key not found in {entry.path}")
    if len(matches) != 1:
        raise ReleaseError(f"TOML version key is duplicated in {entry.path}")
    index, match = matches[0]
    return lines, index, match


def read_version(repo: Path, entry: VersionFile) -> str | None:
    path = repo / entry.path
    if not path.exists():
        if entry.optional:
            return None
        raise ReleaseError(f"missing configured version file: {entry.path}")
    text = path.read_text(encoding="utf-8")
    if entry.kind == "plain":
        lines = text.splitlines()
        if len(lines) != 1 or not lines[0].strip():
            raise ReleaseError(f"plain version file must contain exactly one non-empty line: {entry.path}")
        return lines[0].strip()
    if entry.kind == "json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ReleaseError(f"invalid JSON in {entry.path}: {exc}") from exc
        value = read_json_pointer(data, json_pointer_parts(entry.pointer, entry.path), entry.path)
        if not isinstance(value, str):
            raise ReleaseError(f"version at {entry.path}{entry.pointer} must be a string")
        return value
    _, _, match = toml_version_location(text, entry)
    return match.group(2)


def write_version(repo: Path, entry: VersionFile, version: str) -> bool:
    path = repo / entry.path
    if not path.exists():
        if entry.optional:
            return False
        raise ReleaseError(f"missing configured version file: {entry.path}")
    original = path.read_text(encoding="utf-8")
    if entry.kind == "plain":
        updated = version + "\n"
    elif entry.kind == "json":
        try:
            data = json.loads(original)
        except json.JSONDecodeError as exc:
            raise ReleaseError(f"invalid JSON in {entry.path}: {exc}") from exc
        parts = json_pointer_parts(entry.pointer, entry.path)
        write_json_pointer(data, parts, version, entry.path)
        updated = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    else:
        lines, index, match = toml_version_location(original, entry)
        newline = match.group(4) or ""
        lines[index] = match.group(1) + version + match.group(3) + newline
        updated = "".join(lines)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def configured_versions(repo: Path, config: dict[str, Any]) -> tuple[str, list[tuple[VersionFile, str]]]:
    entries = parse_version_files(config)
    values: list[tuple[VersionFile, str]] = []
    for entry in entries:
        value = read_version(repo, entry)
        if value is not None:
            values.append((entry, validate_semver(value)))
    canonical_path = config.get("canonical_version_file")
    canonical = next((value for entry, value in values if entry.path == canonical_path), None)
    if canonical is None:
        raise ReleaseError("canonical_version_file must name a present version_files entry")
    mismatches = [(entry.path, value) for entry, value in values if value != canonical]
    if mismatches:
        detail = ", ".join(f"{path}={value}" for path, value in mismatches)
        raise ReleaseError(f"version files disagree with {canonical_path}={canonical}: {detail}")
    return canonical, values


def check_forbidden_patterns(repo: Path, config: dict[str, Any]) -> None:
    for index, item in enumerate(config.get("forbidden_version_patterns", []), 1):
        if not isinstance(item, dict):
            raise ReleaseError(f"forbidden_version_patterns[{index}] must be an object")
        path_value = item.get("path")
        regex_value = item.get("regex")
        if not isinstance(path_value, str) or not isinstance(regex_value, str):
            raise ReleaseError(f"forbidden_version_patterns[{index}] requires path and regex")
        path = repo / path_value
        if not path.exists() and item.get("optional", False):
            continue
        if not path.is_file():
            raise ReleaseError(f"forbidden-pattern file is missing: {path_value}")
        try:
            pattern = re.compile(regex_value, re.MULTILINE)
        except re.error as exc:
            raise ReleaseError(f"invalid forbidden regex for {path_value}: {exc}") from exc
        match = pattern.search(path.read_text(encoding="utf-8"))
        if match:
            excerpt = match.group(0).replace("\n", "\\n")
            raise ReleaseError(f"forbidden version literal in {path_value}: {excerpt!r}")



def changelog_path(config: dict[str, Any]) -> str | None:
    raw = config.get("changelog")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ReleaseError("release config changelog must be an object")
    path = raw.get("path")
    if not isinstance(path, str) or not path:
        raise ReleaseError("release config changelog.path must be a non-empty string")
    return path


def check_changelog(repo: Path, config: dict[str, Any]) -> None:
    path_value = changelog_path(config)
    if path_value is None:
        return
    raw = config["changelog"]
    heading = raw.get("unreleased_heading", "## Unreleased")
    if not isinstance(heading, str) or not heading:
        raise ReleaseError("release config changelog.unreleased_heading must be a non-empty string")
    path = repo / path_value
    if not path.is_file():
        raise ReleaseError(f"configured changelog is missing: {path_value}")
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(rf"(?m)^{re.escape(heading)}[ \t]*$", text))
    if len(matches) != 1:
        raise ReleaseError(f"changelog must contain exactly one {heading!r} heading")


def prepare_changelog(repo: Path, config: dict[str, Any], version: str) -> str | None:
    path_value = changelog_path(config)
    if path_value is None:
        return None
    raw = config["changelog"]
    unreleased = raw.get("unreleased_heading", "## Unreleased")
    release_template = raw.get("release_heading", "## {version} — {date}")
    if not isinstance(unreleased, str) or not isinstance(release_template, str):
        raise ReleaseError("changelog headings must be strings")
    if "{version}" not in release_template or "{date}" not in release_template:
        raise ReleaseError("changelog.release_heading must contain {version} and {date}")
    path = repo / path_value
    text = path.read_text(encoding="utf-8")
    matches = list(re.finditer(rf"(?m)^{re.escape(unreleased)}[ \t]*$", text))
    if len(matches) != 1:
        raise ReleaseError(f"changelog must contain exactly one {unreleased!r} heading")
    match = matches[0]
    section_start = match.end()
    next_heading = re.search(r"(?m)^##\s+.+$", text[section_start:])
    section_end = section_start + next_heading.start() if next_heading else len(text)
    if not text[section_start:section_end].strip():
        raise ReleaseError("changelog Unreleased section is empty")
    date = datetime.now(timezone.utc).date().isoformat()
    release_heading = release_template.format(version=version, date=date)
    if re.search(rf"(?m)^{re.escape(release_heading)}[ \t]*$", text):
        raise ReleaseError(f"changelog already contains release heading: {release_heading}")
    insertion = f"\n\n{release_heading}"
    updated = text[:section_start] + insertion + text[section_start:]
    path.write_text(updated, encoding="utf-8")
    return path_value


def status_paths(repo: Path) -> set[str]:
    result = run_git(repo, "status", "--porcelain=v1", "-z")
    paths: set[str] = set()
    fields = result.stdout.split("\0")
    index = 0
    while index < len(fields):
        record = fields[index]
        index += 1
        if not record:
            continue
        if len(record) < 4:
            raise ReleaseError(f"unexpected git status record: {record!r}")
        status = record[:2]
        path = record[3:]
        paths.add(path)
        if any(code in status for code in ("R", "C")):
            if index >= len(fields) or not fields[index]:
                raise ReleaseError(f"rename/copy status is missing its source path: {record!r}")
            paths.add(fields[index])
            index += 1
    return paths


def ensure_clean(repo: Path) -> None:
    paths = status_paths(repo)
    if paths:
        raise ReleaseError("working tree must be clean: " + ", ".join(sorted(paths)))


def current_head(repo: Path) -> str:
    return run_git(repo, "rev-parse", "HEAD").stdout.strip()


def command_check(repo: Path, config: dict[str, Any]) -> None:
    version, values = configured_versions(repo, config)
    check_forbidden_patterns(repo, config)
    check_changelog(repo, config)
    print(f"PASS: version {version}")
    for entry, value in values:
        print(f"  {entry.path}: {value}")


def command_prepare(repo: Path, config: dict[str, Any], version: str) -> None:
    ensure_clean(repo)
    version = validate_semver(version)
    current, _ = configured_versions(repo, config)
    if version == current:
        raise ReleaseError(f"requested version is already current: {version}")
    changed: list[str] = []
    for entry in parse_version_files(config):
        if write_version(repo, entry, version):
            changed.append(entry.path)
    changed_changelog = prepare_changelog(repo, config, version)
    if changed_changelog:
        changed.append(changed_changelog)
    command_check(repo, config)
    if not changed:
        raise ReleaseError("prepare changed no files")
    print("Prepared version files:")
    for path in changed:
        print(f"  {path}")


def command_commit(repo: Path, config: dict[str, Any]) -> None:
    version, values = configured_versions(repo, config)
    check_forbidden_patterns(repo, config)
    check_changelog(repo, config)
    allowed = {entry.path for entry, _ in values}
    configured_changelog = changelog_path(config)
    if configured_changelog:
        allowed.add(configured_changelog)
    changed = status_paths(repo)
    if not changed:
        raise ReleaseError("no version changes to commit")
    unexpected = sorted(changed - allowed)
    if unexpected:
        raise ReleaseError("release commit contains non-version paths: " + ", ".join(unexpected))
    canonical = str(config["canonical_version_file"])
    if canonical not in changed:
        raise ReleaseError(f"canonical version file is unchanged: {canonical}")
    run_git(repo, "add", "--", *sorted(changed))
    message_template = config.get("release_commit_message", "chore(release): v{version}")
    if not isinstance(message_template, str) or "{version}" not in message_template:
        raise ReleaseError("release_commit_message must contain {version}")
    message = message_template.format(version=version)
    run_git(repo, "commit", "-m", message)
    print(f"Created release commit {current_head(repo)} for v{version}")


def command_tag(repo: Path, config: dict[str, Any]) -> None:
    ensure_clean(repo)
    version, _ = configured_versions(repo, config)
    prefix = str(config.get("tag_prefix", "v"))
    tag = prefix + version
    if run_git(repo, "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}", check=False).returncode == 0:
        raise ReleaseError(f"tag already exists: {tag}")
    run_git(repo, "tag", "-a", tag, "-m", tag)
    print(f"Created annotated tag {tag} at {current_head(repo)}")
    print(f"Push explicitly with: git push origin {tag}")


def command_verify_tag(repo: Path, config: dict[str, Any], tag: str) -> None:
    version, _ = configured_versions(repo, config)
    expected = str(config.get("tag_prefix", "v")) + version
    if tag != expected:
        raise ReleaseError(f"tag/version mismatch: tag={tag}, expected={expected}")
    tag_commit = run_git(repo, "rev-parse", f"{tag}^{{commit}}").stdout.strip()
    head = current_head(repo)
    if tag_commit != head:
        raise ReleaseError(f"tag {tag} resolves to {tag_commit}, but HEAD is {head}")
    print(f"PASS: {tag} matches repository version and HEAD {head}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synchronize, commit, and tag repository versions safely.")
    parser.add_argument("--repo", help="Repository root. Defaults to the parent of scripts/.")
    parser.add_argument("--config", default="release-config.json", help="Config path relative to repository root.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="Verify configured version files and forbidden literals.")
    prepare = subparsers.add_parser("prepare", help="Update all configured version files.")
    prepare.add_argument("version")
    subparsers.add_parser("commit", help="Commit only configured version-file changes.")
    subparsers.add_parser("tag", help="Create an annotated tag for the current repository version.")
    verify = subparsers.add_parser("verify-tag", help="Verify a tag matches VERSION and HEAD.")
    verify.add_argument("tag")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        repo = repository_root(args.repo)
        config = load_config(repo, args.config)
        if args.command == "check":
            command_check(repo, config)
        elif args.command == "prepare":
            command_prepare(repo, config, args.version)
        elif args.command == "commit":
            command_commit(repo, config)
        elif args.command == "tag":
            command_tag(repo, config)
        elif args.command == "verify-tag":
            command_verify_tag(repo, config, args.tag)
        else:
            parser.error(f"unsupported command: {args.command}")
    except ReleaseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
