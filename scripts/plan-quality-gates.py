#!/usr/bin/env python3
"""Build a deterministic, read-only quality-gate execution plan."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
STATUS_RE = re.compile(r"^(?:[AMDT]|R[0-9]+|C[0-9]+)$")
PHASES = {"prepare", "merge"}
STATUSES = {"A", "M", "D", "T", "R"}


class QualityGatePlanError(ValueError):
    """Raised when a quality-gate plan cannot be built or validated."""


def _fail(message: str) -> None:
    raise QualityGatePlanError(message)


def _quality_validator():
    path = Path(__file__).with_name("validate-quality-gates.py")
    spec = importlib.util.spec_from_file_location("quality_gates_validator_for_plan", path)
    if spec is None or spec.loader is None:
        _fail("cannot load the quality-gates validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip()
        _fail(f"git {' '.join(arguments)} failed: {detail or 'exit status ' + str(result.returncode)}")
    return result.stdout


def _decode(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail(f"{label} is not valid UTF-8")
        raise AssertionError from exc


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        _fail(f"{label} must be a 40-character lowercase commit SHA")
    return value


def _safe_path(value: Any, label: str, *, glob: bool = False) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{label} must be a non-empty repository-relative path")
    if len(value) > 4096 or value.startswith("/") or "\\" in value:
        _fail(f"{label} must be a normalized repository-relative POSIX path")
    if CONTROL_RE.search(value) or re.match(r"^[A-Za-z]:/", value):
        _fail(f"{label} contains an unsafe character")
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        _fail(f"{label} must not contain empty or traversal segments")
    if ".git" in segments:
        _fail(f"{label} must not address .git internals")
    if not glob and any(character in value for character in "*?[]"):
        _fail(f"{label} must be an exact path")
    return value


def _relative_declaration(repo: Path, value: str) -> tuple[str, Path, bytes]:
    if os.path.isabs(value):
        _fail("declaration must be repository-relative")
    relative = _safe_path(value, "declaration")
    candidate = repo.joinpath(*relative.split("/"))
    cursor = repo
    for segment in relative.split("/"):
        cursor = cursor / segment
        if cursor.is_symlink():
            _fail("declaration must not contain symlinks")
    try:
        resolved = candidate.resolve(strict=True)
        if os.path.commonpath((str(repo), str(resolved))) != str(repo):
            _fail("declaration must remain inside the repository")
    except FileNotFoundError:
        _fail("declaration does not exist")
    if not candidate.is_file():
        _fail("declaration must be a regular file")
    try:
        data = candidate.read_bytes()
    except OSError as exc:
        _fail(f"cannot read declaration: {exc}")
    return relative, candidate, data


def _repository_root(argument: str) -> Path:
    supplied = Path(argument).expanduser()
    if not supplied.exists():
        _fail("repository does not exist")
    try:
        root_text = _decode(_git(supplied, "rev-parse", "--show-toplevel").strip(), "repository root")
        bare = _decode(_git(supplied, "rev-parse", "--is-bare-repository").strip(), "repository mode")
        inside = _decode(_git(supplied, "rev-parse", "--is-inside-work-tree").strip(), "repository mode")
    except (OSError, subprocess.SubprocessError) as exc:
        _fail(f"not a usable Git repository: {exc}")
    if bare == "true" or inside != "true":
        _fail("repository must be a non-bare worktree")
    root = Path(root_text).resolve()
    if not root.is_dir():
        _fail("repository root is not a directory")
    return root


def _resolve_commit(repo: Path, value: str, label: str) -> str:
    _sha(value, label)
    resolved = _decode(_git(repo, "rev-parse", "--verify", f"{value}^{{commit}}").strip(), label)
    if resolved != value:
        _fail(f"{label} is not the exact requested commit")
    return value


def _parse_nul_tokens(data: bytes, label: str) -> list[bytes]:
    if not data:
        return []
    parts = data.split(b"\0")
    if parts[-1] != b"":
        _fail(f"{label} is not NUL terminated")
    return parts[:-1]


def _parse_diff_records(data: bytes, label: str) -> list[dict[str, Any]]:
    tokens = _parse_nul_tokens(data, label)
    records: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        status = _decode(tokens[index], f"{label} status")
        index += 1
        if not STATUS_RE.fullmatch(status):
            _fail(f"{label} contains unsupported or unmerged status {status!r}")
        code = status[0]
        if code in {"A", "M", "D", "T"}:
            if index >= len(tokens):
                _fail(f"{label} has a truncated {status} record")
            path = _safe_path(_decode(tokens[index], f"{label} path"), f"{label} path")
            records.append({"status": code, "path": path})
            index += 1
            continue
        if index + 1 >= len(tokens):
            _fail(f"{label} has a truncated {status} record")
        source = _safe_path(_decode(tokens[index], f"{label} source"), f"{label} source")
        destination = _safe_path(_decode(tokens[index + 1], f"{label} destination"), f"{label} destination")
        if source == destination:
            _fail(f"{label} contains an ambiguous rename")
        if code == "C":
            _fail("copy status is not supported by the B1 selector")
        records.append({"status": "R", "source": source, "path": destination})
        index += 2
    seen: set[str] = set()
    for record in records:
        paths = [record["path"]]
        if record["status"] == "R":
            paths.append(record["source"])
        for path in paths:
            if path in seen:
                _fail(f"ambiguous duplicate changed path: {path}")
            seen.add(path)
    return records


def _status_projection(data: bytes) -> list[str]:
    tokens = _parse_nul_tokens(data, "worktree status")
    projection: list[str] = []
    index = 0
    while index < len(tokens):
        token = _decode(tokens[index], "worktree status")
        if len(token) < 4 or token[2] != " ":
            _fail("malformed worktree status record")
        xy = token[:2]
        path = _safe_path(token[3:], "worktree status path")
        if "U" in xy:
            _fail("conflicted worktree status is not supported")
        projection.append(f"{xy} {path}")
        index += 1
        if "R" in xy or "C" in xy:
            if index >= len(tokens):
                _fail("truncated worktree rename/copy status")
            projection.append(_safe_path(_decode(tokens[index], "worktree status source"), "worktree status source"))
            index += 1
    return projection


def _tree_has_gitlink(repo: Path, revision: str, paths: list[str]) -> bool:
    if not paths:
        return False
    data = _git(repo, "ls-tree", "-r", "-z", "--full-tree", revision, "--", *paths)
    for token in _parse_nul_tokens(data, "tree entries"):
        try:
            header, _path = token.split(b"\t", 1)
        except ValueError:
            _fail("malformed tree entry")
        fields = header.split()
        if not fields or fields[0] == b"160000":
            return True
    return False


def _index_has_gitlink(repo: Path, paths: list[str]) -> bool:
    if not paths:
        return False
    data = _git(repo, "ls-files", "--stage", "-z", "--", *paths)
    for token in _parse_nul_tokens(data, "index entries"):
        try:
            header, _path = token.split(b"\t", 1)
        except ValueError:
            _fail("malformed index entry")
        fields = header.split()
        if not fields or fields[0] == b"160000":
            return True
    return False


def _file_digest(path: Path) -> bytes:
    digest = hashlib.sha256()
    info = path.lstat()
    if path.is_symlink():
        digest.update(b"symlink\0")
        digest.update(os.readlink(path).encode("utf-8", "strict"))
    elif os.path.isfile(path):
        digest.update(b"file\0")
        digest.update(str(info.st_mode).encode("ascii"))
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    else:
        _fail(f"unsupported untracked filesystem object: {path.name}")
    return digest.digest()


def _worktree_fingerprint(repo: Path, base: str, status_raw: bytes, untracked: list[str]) -> str:
    digest = hashlib.sha256()
    for label, data in (
        (b"status", status_raw),
        (b"worktree-diff", _git(repo, "diff", "--binary", "--no-ext-diff", "--no-textconv", base, "--")),
        (b"index-diff", _git(repo, "diff", "--cached", "--binary", "--no-ext-diff", "--no-textconv", base, "--")),
    ):
        digest.update(label + b"\0" + len(data).to_bytes(8, "big") + data)
    for relative in sorted(untracked):
        digest.update(relative.encode("utf-8") + b"\0" + _file_digest(repo / relative))
    return digest.hexdigest()


def _collect_changes(repo: Path, base: str, target: str) -> tuple[list[dict[str, Any]], list[str], str, list[str]]:
    if target == "WORKTREE":
        unmerged = _git(repo, "ls-files", "--unmerged", "-z", "--")
        if unmerged:
            _fail("conflicted index entries are not supported")
        status_raw = _git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--")
        projection = _status_projection(status_raw)
        diff_raw = _git(
            repo,
            "diff",
            "--name-status",
            "-z",
            "-M",
            "-C",
            "--find-copies-harder",
            "--no-ext-diff",
            "--no-textconv",
            base,
            "--",
        )
        records = _parse_diff_records(diff_raw, "worktree diff")
        untracked_raw = _git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--")
        untracked = []
        for token in _parse_nul_tokens(untracked_raw, "untracked paths"):
            untracked.append(_safe_path(_decode(token, "untracked path"), "untracked path"))
        seen = {record["path"] for record in records}
        seen.update(record["source"] for record in records if record["status"] == "R")
        for path in untracked:
            if path in seen:
                _fail(f"ambiguous duplicate changed path: {path}")
            records.append({"status": "A", "path": path})
            seen.add(path)
        paths = sorted(seen)
        if _tree_has_gitlink(repo, base, paths) or _index_has_gitlink(repo, paths):
            _fail("submodule or gitlink changes are not supported")
        fingerprint = _worktree_fingerprint(repo, base, status_raw, untracked)
        return _sort_records(records), paths, fingerprint, projection

    diff_raw = _git(
        repo,
        "diff",
        "--name-status",
        "-z",
        "-M",
        "-C",
        "--find-copies-harder",
        "--no-ext-diff",
        "--no-textconv",
        base,
        target,
        "--",
    )
    records = _parse_diff_records(diff_raw, "committed diff")
    paths = sorted({path for record in records for path in ([record["path"]] + ([record["source"]] if record["status"] == "R" else []))})
    if _tree_has_gitlink(repo, base, paths) or _tree_has_gitlink(repo, target, paths):
        _fail("submodule or gitlink changes are not supported")
    return _sort_records(records), paths, "", []


def _current_worktree_state(repo: Path, base: str) -> tuple[str, str]:
    """Return the exact HEAD and fingerprint used for a WORKTREE plan check."""
    head = _decode(_git(repo, "rev-parse", "--verify", "HEAD^{commit}").strip(), "HEAD")
    _resolve_commit(repo, head, "HEAD")
    status_raw = _git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--")
    untracked = [
        _safe_path(_decode(token, "untracked path"), "untracked path")
        for token in _parse_nul_tokens(
            _git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--"),
            "untracked paths",
        )
    ]
    return head, _worktree_fingerprint(repo, base, status_raw, untracked)


def _sort_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records, key=lambda item: (item["path"], item.get("source", ""), item["status"]))


@lru_cache(maxsize=4096)
def _match_segments(pattern: tuple[str, ...], path: tuple[str, ...], pattern_index: int = 0, path_index: int = 0) -> bool:
    if pattern_index == len(pattern):
        return path_index == len(path)
    segment = pattern[pattern_index]
    if segment == "**":
        return _match_segments(pattern, path, pattern_index + 1, path_index) or (
            path_index < len(path) and _match_segments(pattern, path, pattern_index, path_index + 1)
        )
    return (
        path_index < len(path)
        and fnmatch.fnmatchcase(path[path_index], segment)
        and _match_segments(pattern, path, pattern_index + 1, path_index + 1)
    )


def match_repository_glob(pattern: str, path: str) -> bool:
    """Match a complete repository-relative POSIX path case-sensitively."""
    return _match_segments(tuple(pattern.split("/")), tuple(path.split("/")))


def _select(declaration: dict[str, Any], phase: str, material_paths: list[str]) -> dict[str, Any]:
    selected_rules: list[dict[str, Any]] = []
    command_entries: list[dict[str, Any]] = []
    command_by_id: dict[str, dict[str, Any]] = {}
    for rule in declaration["rules"]:
        matched = sorted({path for path in material_paths if any(match_repository_glob(pattern, path) for pattern in rule["paths"])})
        if not matched:
            continue
        selected_rules.append({"id": rule["id"], "matched_paths": matched})
        for command in rule[phase]:
            existing = command_by_id.get(command["id"])
            if existing is None:
                existing = {
                    "id": command["id"],
                    "argv": list(command["argv"]),
                    "mode": command["mode"],
                    "file_args": command["file_args"],
                    "timeout_seconds": command["timeout_seconds"],
                    "matched_paths": set(matched),
                }
                command_by_id[command["id"]] = existing
                command_entries.append(existing)
            else:
                existing["matched_paths"].update(matched)
    for command in command_entries:
        matched = sorted(command["matched_paths"])
        if command["file_args"] != "none" and not matched:
            _fail(f"selected command {command['id']} requires matched paths")
        if command["file_args"] == "none":
            invocations = [list(command["argv"])]
        elif command["file_args"] == "append":
            invocations = [list(command["argv"]) + matched]
        else:
            invocations = [list(command["argv"]) + [path] for path in matched]
        command["matched_paths"] = matched
        command["invocations"] = invocations
    unmatched = [path for path in material_paths if not any(match_repository_glob(pattern, path) for rule in declaration["rules"] for pattern in rule["paths"])]
    if unmatched:
        _fail("unmatched changed paths: " + ", ".join(unmatched[:32]))
    generated_entries: list[dict[str, Any]] = []
    if phase == "prepare":
        for generated in declaration["generated"]:
            matched_inputs = sorted({path for path in material_paths if any(match_repository_glob(pattern, path) for pattern in generated["inputs"])})
            if matched_inputs:
                generated_entries.append(
                    {
                        "id": generated["id"],
                        "matched_inputs": matched_inputs,
                        "outputs": list(generated["outputs"]),
                        "argv": list(generated["argv"]),
                        "timeout_seconds": generated["timeout_seconds"],
                    }
                )
    return {
        "selected_rules": selected_rules,
        "selected_rule_ids": [rule["id"] for rule in selected_rules],
        "selected_generated": generated_entries,
        "selected_commands": command_entries,
    }


def _exact_object(value: Any, label: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        _fail(f"{label} has unknown or missing fields")
    return value


def _plan_integer(value: Any, label: str, minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail(f"{label} must be an integer >= {minimum}")
    if maximum is not None and value > maximum:
        _fail(f"{label} must be an integer <= {maximum}")
    return value


def _plan_string(value: Any, label: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value) or CONTROL_RE.search(value):
        _fail(f"{label} must be a valid string")
    return value


def validate_execution_plan(plan: Any) -> dict[str, Any]:
    root = _exact_object(
        plan,
        "plan",
        {
            "schema_version",
            "phase",
            "declaration",
            "base_revision",
            "target",
            "changed",
            "selected_rules",
            "selected_rule_ids",
            "selected_generated",
            "cleanup",
            "selected_commands",
            "counts",
        },
    )
    if root["schema_version"] != 1 or isinstance(root["schema_version"], bool):
        _fail("plan.schema_version must be 1")
    if root["phase"] not in PHASES:
        _fail("plan.phase is invalid")
    declaration = _exact_object(root["declaration"], "plan.declaration", {"path", "sha256"})
    _safe_path(declaration["path"], "plan.declaration.path")
    if not HEX64_RE.fullmatch(_plan_string(declaration["sha256"], "plan.declaration.sha256")):
        _fail("plan.declaration.sha256 must be a SHA-256 digest")
    _sha(root["base_revision"], "plan.base_revision")
    target = _exact_object(root["target"], "plan.target", {"kind", "revision", "head_revision", "worktree_fingerprint", "status_projection"})
    if target["kind"] not in {"worktree", "commit"}:
        _fail("plan.target.kind is invalid")
    _sha(target["revision"], "plan.target.revision")
    _sha(target["head_revision"], "plan.target.head_revision")
    fingerprint = _plan_string(target["worktree_fingerprint"], "plan.target.worktree_fingerprint", nonempty=False)
    if fingerprint and not HEX64_RE.fullmatch(fingerprint):
        _fail("plan.target.worktree_fingerprint must be a SHA-256 digest")
    if target["kind"] == "worktree" and not fingerprint:
        _fail("worktree target requires a fingerprint")
    if target["kind"] == "worktree" and target["revision"] != target["head_revision"]:
        _fail("worktree target revision must equal HEAD")
    if target["kind"] == "commit" and (fingerprint or target["status_projection"]):
        _fail("committed target must not contain worktree projection data")
    if not isinstance(target["status_projection"], list):
        _fail("plan.target.status_projection must be an array")
    for index, item in enumerate(target["status_projection"]):
        _plan_string(item, f"plan.target.status_projection[{index}]")
    changed = _exact_object(root["changed"], "plan.changed", {"records", "material_paths"})
    records = changed["records"]
    if not isinstance(records, list):
        _fail("plan.changed.records must be an array")
    material = changed["material_paths"]
    if not isinstance(material, list) or material != sorted(material) or len(set(material)) != len(material):
        _fail("plan.changed.material_paths must be sorted and unique")
    for index, path in enumerate(material):
        _safe_path(path, f"plan.changed.material_paths[{index}]")
    record_paths: list[str] = []
    previous_key: tuple[str, str, str] | None = None
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            _fail(f"plan.changed.records[{index}] must be an object")
        status = record.get("status")
        if status == "R":
            item = _exact_object(record, f"plan.changed.records[{index}]", {"status", "source", "path"})
            source = _safe_path(item["source"], f"plan.changed.records[{index}].source")
            path = _safe_path(item["path"], f"plan.changed.records[{index}].path")
            if source == path:
                _fail("rename source and destination must differ")
            record_paths.extend((source, path))
        elif status in {"A", "M", "D", "T"}:
            item = _exact_object(record, f"plan.changed.records[{index}]", {"status", "path"})
            path = _safe_path(item["path"], f"plan.changed.records[{index}].path")
            record_paths.append(path)
            source = ""
        else:
            _fail(f"plan.changed.records[{index}] has an invalid status")
        key = (path, source, status)
        if previous_key is not None and key < previous_key:
            _fail("plan.changed.records must be canonically sorted")
        previous_key = key
    if len(record_paths) != len(set(record_paths)) or sorted(set(record_paths)) != material:
        _fail("plan.changed.material_paths does not match changed records")
    selected_rules = root["selected_rules"]
    if not isinstance(selected_rules, list):
        _fail("plan.selected_rules must be an array")
    rule_ids: list[str] = []
    for index, rule in enumerate(selected_rules):
        item = _exact_object(rule, f"plan.selected_rules[{index}]", {"id", "matched_paths"})
        rule_id = _plan_string(item["id"], f"plan.selected_rules[{index}].id")
        if len(rule_id) > 64 or not ID_RE.fullmatch(rule_id) or rule_id in rule_ids:
            _fail("selected rule IDs must be unique valid identifiers")
        paths = item["matched_paths"]
        if not isinstance(paths, list) or not paths or paths != sorted(paths) or len(set(paths)) != len(paths):
            _fail("selected rule paths must be sorted and unique")
        for path in paths:
            _safe_path(path, "selected rule path")
            if path not in material:
                _fail("selected rule path is not a material changed path")
        rule_ids.append(rule_id)
    if root["selected_rule_ids"] != rule_ids:
        _fail("selected_rule_ids must mirror selected_rules order")
    generated = root["selected_generated"]
    if not isinstance(generated, list):
        _fail("plan.selected_generated must be an array")
    generated_ids: set[str] = set()
    for index, item in enumerate(generated):
        entry = _exact_object(item, f"plan.selected_generated[{index}]", {"id", "matched_inputs", "outputs", "argv", "timeout_seconds"})
        generated_id = _plan_string(entry["id"], f"plan.selected_generated[{index}].id")
        if len(generated_id) > 64 or not ID_RE.fullmatch(generated_id) or generated_id in generated_ids:
            _fail("selected generated IDs must be unique valid identifiers")
        generated_ids.add(generated_id)
        for field in ("matched_inputs", "outputs"):
            values = entry[field]
            if not isinstance(values, list) or len(set(values)) != len(values) or not values:
                _fail(f"plan.selected_generated[{index}].{field} must be non-empty and unique")
            if field == "matched_inputs" and values != sorted(values):
                _fail(f"plan.selected_generated[{index}].matched_inputs must be sorted and unique")
            for path in values:
                _safe_path(path, f"plan.selected_generated[{index}].{field}")
        if any(path not in material for path in entry["matched_inputs"]):
            _fail("selected generated input is not a material changed path")
        _validate_argv(entry["argv"], f"plan.selected_generated[{index}].argv")
        _plan_integer(entry["timeout_seconds"], f"plan.selected_generated[{index}].timeout_seconds", 1, 3600)
    if root["phase"] == "merge" and generated:
        _fail("plan.selected_generated must be empty for merge phase")
    cleanup = _exact_object(root["cleanup"], "plan.cleanup", {"untracked_only", "paths", "performed"})
    if cleanup["untracked_only"] is not True or cleanup["performed"] is not False:
        _fail("cleanup projection must be untracked-only and not performed")
    if not isinstance(cleanup["paths"], list) or len(set(cleanup["paths"])) != len(cleanup["paths"]):
        _fail("cleanup paths must be unique")
    for path in cleanup["paths"]:
        _safe_path(path, "plan.cleanup.path", glob=True)
    commands = root["selected_commands"]
    if not isinstance(commands, list):
        _fail("plan.selected_commands must be an array")
    command_ids: set[str] = set()
    invocation_count = 0
    for index, command in enumerate(commands):
        item = _exact_object(command, f"plan.selected_commands[{index}]", {"id", "argv", "mode", "file_args", "timeout_seconds", "matched_paths", "invocations"})
        command_id = _plan_string(item["id"], f"plan.selected_commands[{index}].id")
        if len(command_id) > 64 or not ID_RE.fullmatch(command_id) or command_id in command_ids:
            _fail("selected command IDs must be unique valid identifiers")
        command_ids.add(command_id)
        _validate_argv(item["argv"], f"plan.selected_commands[{index}].argv")
        if item["mode"] not in {"check", "fix"} or item["file_args"] not in {"none", "append", "each"}:
            _fail("selected command mode or file_args is invalid")
        if root["phase"] == "merge" and item["mode"] != "check":
            _fail("merge phase commands must be check-only")
        _plan_integer(item["timeout_seconds"], f"plan.selected_commands[{index}].timeout_seconds", 1, 3600)
        paths = item["matched_paths"]
        if not isinstance(paths, list) or paths != sorted(paths) or len(set(paths)) != len(paths):
            _fail("selected command paths must be sorted and unique")
        for path in paths:
            _safe_path(path, "selected command path")
            if path not in material:
                _fail("selected command path is not a material changed path")
        invocations = item["invocations"]
        if not isinstance(invocations, list) or not invocations:
            _fail("selected command invocations must be non-empty")
        if item["file_args"] != "none" and not paths:
            _fail("file_args append/each requires matched paths")
        if item["file_args"] == "none" and (len(invocations) != 1 or invocations[0] != item["argv"]):
            _fail("file_args=none must preserve exactly one argv")
        if item["file_args"] == "append" and (len(invocations) != 1 or invocations[0] != item["argv"] + paths):
            _fail("file_args=append must append sorted matched paths once")
        if item["file_args"] == "each" and invocations != [item["argv"] + [path] for path in paths]:
            _fail("file_args=each must expand one invocation per matched path")
        for invocation in invocations:
            _validate_argv(invocation, f"plan.selected_commands[{index}].invocation")
        invocation_count += len(invocations)
    counts = _exact_object(root["counts"], "plan.counts", {"changed_records", "material_paths", "selected_rules", "selected_generated", "selected_commands", "invocations"})
    expected_counts = {
        "changed_records": len(records),
        "material_paths": len(material),
        "selected_rules": len(selected_rules),
        "selected_generated": len(generated),
        "selected_commands": len(commands),
        "invocations": invocation_count,
    }
    for key, value in counts.items():
        _plan_integer(value, f"plan.counts.{key}")
    if counts != expected_counts:
        _fail("plan.counts does not match the plan contents")
    return root


def _validate_argv(value: Any, label: str) -> None:
    if not isinstance(value, list) or not value:
        _fail(f"{label} must be a non-empty argv array")
    for index, token in enumerate(value):
        if not isinstance(token, str) or not token or CONTROL_RE.search(token):
            _fail(f"{label}[{index}] is not a safe argv token")


def _output_path(repo: Path, argument: str) -> Path:
    raw = Path(argument).expanduser()
    candidate = (Path.cwd() / raw if not raw.is_absolute() else raw).resolve(strict=False)
    if os.path.commonpath((str(repo), str(candidate))) == str(repo):
        _fail("output must be outside the target repository")
    if candidate.exists() or candidate.is_symlink():
        _fail("output already exists")
    if not candidate.parent.is_dir():
        _fail("output parent directory must already exist")
    return candidate


def _atomic_write(path: Path, data: bytes) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except Exception:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass
        raise


def build_plan(repo_argument: str, declaration_argument: str, base_argument: str, phase: str, target_argument: str) -> dict[str, Any]:
    if phase not in PHASES:
        _fail("phase must be prepare or merge")
    if target_argument != "WORKTREE" and not SHA_RE.fullmatch(target_argument):
        _fail("target must be WORKTREE or an exact lowercase commit SHA")
    repo = _repository_root(repo_argument)
    declaration_relative, declaration_path, declaration_bytes = _relative_declaration(repo, declaration_argument)
    validator = _quality_validator()
    try:
        # Validate the exact bytes already read for the emitted digest.  Do not
        # re-open the path: a concurrent replacement must never make the plan
        # describe one declaration while hashing another.
        declaration = validator.load_json_bytes(declaration_bytes, label=str(declaration_path))
    except Exception as exc:
        _fail(f"invalid quality-gates declaration: {exc}")
    base = _resolve_commit(repo, base_argument, "base")
    head = _decode(_git(repo, "rev-parse", "--verify", "HEAD^{commit}").strip(), "HEAD")
    _resolve_commit(repo, head, "HEAD")
    ancestor = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", base, head], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ancestor.returncode:
        _fail("base must be an ancestor of current HEAD")
    target = target_argument
    if target != "WORKTREE":
        _resolve_commit(repo, target, "target")
        ancestor = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", base, target], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if ancestor.returncode:
            _fail("base must be an ancestor of target")
    records, material_paths, fingerprint, status_projection = _collect_changes(repo, base, target)
    selected = _select(declaration, phase, material_paths)
    if target == "WORKTREE":
        current_head, current_fingerprint = _current_worktree_state(repo, base)
        if current_head != head or current_fingerprint != fingerprint:
            _fail("worktree changed during plan collection")
    cleanup = {
        "untracked_only": declaration["cleanup"]["untracked_only"],
        "paths": list(declaration["cleanup"]["paths"]),
        "performed": False,
    }
    plan = {
        "schema_version": 1,
        "phase": phase,
        "declaration": {
            "path": declaration_relative,
            "sha256": hashlib.sha256(declaration_bytes).hexdigest(),
        },
        "base_revision": base,
        "target": {
            "kind": "worktree" if target == "WORKTREE" else "commit",
            "revision": head if target == "WORKTREE" else target,
            "head_revision": head,
            "worktree_fingerprint": fingerprint,
            "status_projection": status_projection,
        },
        "changed": {"records": records, "material_paths": material_paths},
        "selected_rules": selected["selected_rules"],
        "selected_rule_ids": selected["selected_rule_ids"],
        "selected_generated": selected["selected_generated"],
        "cleanup": cleanup,
        "selected_commands": selected["selected_commands"],
        "counts": {
            "changed_records": len(records),
            "material_paths": len(material_paths),
            "selected_rules": len(selected["selected_rules"]),
            "selected_generated": len(selected["selected_generated"]),
            "selected_commands": len(selected["selected_commands"]),
            "invocations": sum(len(item["invocations"]) for item in selected["selected_commands"]),
        },
    }
    validate_execution_plan(plan)
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--declaration", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--phase", required=True, choices=sorted(PHASES))
    parser.add_argument("--target", default="WORKTREE")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        repo = _repository_root(args.repo)
        output = _output_path(repo, args.output)
        plan = build_plan(args.repo, args.declaration, args.base, args.phase, args.target)
        encoded = (json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        _atomic_write(output, encoded)
    except (QualityGatePlanError, OSError, ValueError) as exc:
        print(f"INVALID quality-gate plan: {exc}", file=sys.stderr)
        return 1
    print(f"Quality-gate plan prepared: phase={args.phase} target={args.target} changed={plan['counts']['material_paths']} commands={plan['counts']['selected_commands']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
