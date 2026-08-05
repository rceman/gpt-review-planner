#!/usr/bin/env python3
"""Validate the dependency-free quality-gates declaration."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any


class QualityGatesError(ValueError):
    """Raised when a quality-gates declaration is invalid."""


ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
GLOB_META = set("*?[]")
SHELL_NAMES = {"sh", "dash", "bash", "zsh", "ksh", "fish"}
CMD_NAMES = {"cmd", "cmd.exe"}
POWERSHELL_NAMES = {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}
CODE_INTERPRETERS = {"python", "python2", "python3", "node", "nodejs", "ruby", "perl"}
BROAD_CLEANUP = {".", "*", "**", "**/*", "/"}
MAX_STRING = 4096


def _fail(path: str, message: str) -> None:
    raise QualityGatesError(f"{path}: {message}")


def _exact_object(value: Any, path: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "must be an object")
    if set(value) != keys:
        missing = sorted(keys - set(value))
        unknown = sorted(set(value) - keys)
        detail = []
        if missing:
            detail.append(f"missing {','.join(missing)}")
        if unknown:
            detail.append(f"unknown {','.join(unknown)}")
        _fail(path, "; ".join(detail))
    return value


def _string(value: Any, path: str, *, max_length: int = MAX_STRING) -> str:
    if not isinstance(value, str) or not value:
        _fail(path, "must be a non-empty string")
    if len(value) > max_length:
        _fail(path, f"must be at most {max_length} characters")
    return value


def _integer(value: Any, path: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(path, "must be an integer")
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        _fail(path, "must be an integer")
    result = int(value)
    if minimum is not None and result < minimum:
        _fail(path, f"must be at least {minimum}")
    if maximum is not None and result > maximum:
        _fail(path, f"must be at most {maximum}")
    return result


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        _fail(path, "must be boolean")
    return value


def _array(value: Any, path: str, *, minimum: int = 0, maximum: int = 256) -> list[Any]:
    if not isinstance(value, list):
        _fail(path, "must be an array")
    if len(value) < minimum or len(value) > maximum:
        _fail(path, f"must contain between {minimum} and {maximum} items")
    return value


def _unique(values: list[Any], path: str) -> None:
    try:
        if len(set(values)) != len(values):
            _fail(path, "must contain unique values")
    except TypeError:
        _fail(path, "must contain hashable values")


def _id(value: Any, path: str) -> str:
    value = _string(value, path, max_length=64)
    if not ID_RE.fullmatch(value):
        _fail(path, "must be lowercase hyphenated identifier")
    return value


def _relative_path(value: Any, path: str, *, glob: bool = True, cleanup: bool = False) -> str:
    value = _string(value, path, max_length=1024)
    if value in BROAD_CLEANUP and cleanup:
        _fail(path, "broad or universal cleanup pattern is forbidden")
    if value.startswith("/") or "\\" in value:
        _fail(path, "must be repository-relative POSIX path")
    if CONTROL_RE.search(value):
        _fail(path, "must not contain control characters")
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        _fail(path, "must have normalized non-empty path segments")
    if not glob and any(char in GLOB_META for char in value):
        _fail(path, "must be an exact path, not a glob")
    return value


def _argv(value: Any, path: str) -> list[str]:
    values = _array(value, path, minimum=1, maximum=128)
    result: list[str] = []
    for index, item in enumerate(values):
        token = _string(item, f"{path}[{index}]")
        if CONTROL_RE.search(token):
            _fail(f"{path}[{index}]", "must not contain control or NUL characters")
        result.append(token)
    return result


def _basename(token: str) -> str:
    return token.replace("\\", "/").rsplit("/", 1)[-1].lower()


def _reject_shell_evaluation(argv: list[str], path: str) -> None:
    for index, token in enumerate(argv):
        name = _basename(token)
        lowered = token.lower()
        next_tokens = argv[index + 1 :]
        if name in SHELL_NAMES:
            if any(item == "-c" or item.startswith("-c") or item in {"--command", "--command=..."} for item in next_tokens):
                _fail(path, "shell command-string evaluation is forbidden")
        elif name in CMD_NAMES:
            if any(item.lower() == "/c" or item.lower().startswith("/c") or item.lower() == "/k" or item.lower().startswith("/k") for item in next_tokens):
                _fail(path, "cmd command-string evaluation is forbidden")
        elif name in POWERSHELL_NAMES:
            switches = {"-command", "-c", "-encodedcommand", "-enc", "-e", "-encodedarguments"}
            if any(item.lower() in switches or item.lower().startswith("-command:") for item in next_tokens):
                _fail(path, "PowerShell command-string evaluation is forbidden")
        elif name in CODE_INTERPRETERS:
            if any(item == "-c" or item == "-e" or item.startswith("-c") for item in next_tokens):
                _fail(path, "inline interpreter evaluation is forbidden")
        _ = lowered


def _command(value: Any, path: str, phase: str) -> dict[str, Any]:
    item = _exact_object(value, path, {"id", "argv", "mode", "file_args", "timeout_seconds"})
    _id(item["id"], f"{path}.id")
    argv = _argv(item["argv"], f"{path}.argv")
    _reject_shell_evaluation(argv, f"{path}.argv")
    mode = item["mode"]
    if mode not in {"check", "fix"}:
        _fail(f"{path}.mode", "must be check or fix")
    if phase in {"merge", "release"} and mode != "check":
        _fail(f"{path}.mode", f"{phase} commands must be check-only")
    file_args = item["file_args"]
    if file_args not in {"none", "append", "each"}:
        _fail(f"{path}.file_args", "must be none, append, or each")
    if phase == "release" and file_args != "none":
        _fail(f"{path}.file_args", "release commands require file_args=none")
    _integer(item["timeout_seconds"], f"{path}.timeout_seconds", minimum=1, maximum=3600)
    return item


def _command_list(value: Any, path: str, phase: str, command_ids: set[str], *, minimum: int = 0) -> None:
    commands = _array(value, path, minimum=minimum, maximum=128)
    for index, command in enumerate(commands):
        item = _command(command, f"{path}[{index}]", phase)
        command_id = item["id"]
        if command_id in command_ids:
            _fail(f"{path}[{index}].id", "command id must be globally unique")
        command_ids.add(command_id)


def _validate_cleanup(value: Any) -> None:
    item = _exact_object(value, "cleanup", {"untracked_only", "paths"})
    if _boolean(item["untracked_only"], "cleanup.untracked_only") is not True:
        _fail("cleanup.untracked_only", "must be exactly true")
    paths = _array(item["paths"], "cleanup.paths", maximum=256)
    seen: set[str] = set()
    for index, path in enumerate(paths):
        normalized = _relative_path(path, f"cleanup.paths[{index}]", cleanup=True)
        if normalized in seen:
            _fail(f"cleanup.paths[{index}]", "must be unique")
        seen.add(normalized)


def _validate_generated(value: Any) -> None:
    generated = _array(value, "generated", maximum=128)
    ids: set[str] = set()
    outputs: set[str] = set()
    for index, generated_rule in enumerate(generated):
        path = f"generated[{index}]"
        item = _exact_object(generated_rule, path, {"id", "input_globs", "output_paths", "argv", "timeout_seconds"})
        rule_id = _id(item["id"], f"{path}.id")
        if rule_id in ids:
            _fail(f"{path}.id", "generated rule id must be unique")
        ids.add(rule_id)
        inputs = _array(item["input_globs"], f"{path}.input_globs", minimum=1, maximum=256)
        _unique(inputs, f"{path}.input_globs")
        for input_index, input_glob in enumerate(inputs):
            _relative_path(input_glob, f"{path}.input_globs[{input_index}]")
        output_paths = _array(item["output_paths"], f"{path}.output_paths", minimum=1, maximum=256)
        _unique(output_paths, f"{path}.output_paths")
        for output_index, output_path in enumerate(output_paths):
            normalized = _relative_path(output_path, f"{path}.output_paths[{output_index}]", glob=False)
            if normalized in outputs:
                _fail(f"{path}.output_paths[{output_index}]", "generated output path must be globally unique")
            outputs.add(normalized)
        _argv(item["argv"], f"{path}.argv")
        _reject_shell_evaluation(item["argv"], f"{path}.argv")
        _integer(item["timeout_seconds"], f"{path}.timeout_seconds", minimum=1, maximum=3600)


def _validate_rules(value: Any) -> set[str]:
    rules = _array(value, "rules", maximum=128)
    ids: set[str] = set()
    command_ids: set[str] = set()
    for index, changed_rule in enumerate(rules):
        path = f"rules[{index}]"
        item = _exact_object(changed_rule, path, {"id", "paths", "prepare", "merge"})
        rule_id = _id(item["id"], f"{path}.id")
        if rule_id in ids:
            _fail(f"{path}.id", "changed-path rule id must be globally unique")
        ids.add(rule_id)
        paths = _array(item["paths"], f"{path}.paths", minimum=1, maximum=256)
        _unique(paths, f"{path}.paths")
        for path_index, changed_path in enumerate(paths):
            _relative_path(changed_path, f"{path}.paths[{path_index}]")
        _command_list(item["prepare"], f"{path}.prepare", "prepare", command_ids)
        _command_list(item["merge"], f"{path}.merge", "merge", command_ids)
        if not item["prepare"] and not item["merge"]:
            _fail(path, "prepare and merge cannot both be empty")
    return command_ids


def validate(document: Any) -> dict[str, Any]:
    root = _exact_object(
        document,
        "$",
        {"schema_version", "unmatched_changed_path", "cleanup", "generated", "rules", "release"},
    )
    _integer(root["schema_version"], "schema_version", minimum=1, maximum=1)
    if root["unmatched_changed_path"] != "reject":
        _fail("unmatched_changed_path", "must be exactly reject")
    _validate_cleanup(root["cleanup"])
    _validate_generated(root["generated"])
    command_ids = _validate_rules(root["rules"])
    _command_list(root["release"], "release", "release", command_ids, minimum=1)
    return root


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise QualityGatesError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: str | os.PathLike[str]) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink():
        raise QualityGatesError("input must not be a symlink")
    if not source.is_file():
        raise QualityGatesError("input must be a regular file")
    try:
        text = source.read_text(encoding="utf-8")
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except QualityGatesError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise QualityGatesError(f"cannot load JSON: {exc}") from exc
    return validate(value)


def validate_file(path: str | os.PathLike[str]) -> dict[str, Any]:
    return load_json(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="quality-gates.json path")
    args = parser.parse_args(argv)
    try:
        load_json(args.path)
    except (QualityGatesError, OSError) as exc:
        print(f"INVALID quality gates: {exc}", file=sys.stderr)
        return 1
    print(f"VALID quality gates: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
