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
SHELL_NAMES = {"sh", "dash", "bash"}
UNSUPPORTED_LAUNCHERS = {
    "zsh",
    "ksh",
    "fish",
    "python2",
    "pypy",
    "pypy3",
    "ruby",
    "perl",
    "cmd",
    "cmd.exe",
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
}
PYTHON_NAMES = {"python", "python3"}
NODE_NAMES = {"node", "nodejs"}
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
    if cleanup and not any(char not in GLOB_META for segment in segments for char in segment):
        _fail(path, "wildcard-only cleanup pattern is forbidden")
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


ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")


def _effective_executable(argv: list[str], path: str) -> tuple[str, int]:
    """Return the effective executable, allowing one transparent env prefix."""
    if _basename(argv[0]) != "env":
        return _basename(argv[0]), 0
    index = 1
    while index < len(argv):
        token = argv[index]
        if token == "--":
            index += 1
            break
        if ENV_ASSIGNMENT_RE.fullmatch(token):
            index += 1
            continue
        if token in {"-i", "--ignore-environment"}:
            index += 1
            continue
        if token in {"-u", "--unset"}:
            if index + 1 >= len(argv) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", argv[index + 1]):
                _fail(path, "env unset option must name an environment variable")
            index += 2
            continue
        if token.startswith("--unset="):
            if not re.fullmatch(r"--unset=[A-Za-z_][A-Za-z0-9_]*", token):
                _fail(path, "env unset option must name an environment variable")
            index += 1
            continue
        if token.startswith("-"):
            _fail(path, "unsupported env option cannot be treated as transparent")
        break
    if index >= len(argv):
        _fail(path, "env prefix must be followed by an executable")
    return _basename(argv[index]), index


def _has_short_command_switch(token: str) -> bool:
    return token.startswith("-") and not token.startswith("--") and "c" in token[1:]


def _consume_launcher_value(argv: list[str], index: int, path: str, *, allowed=None) -> int:
    """Consume one value for a recognized launcher option.

    Values that look like options are rejected so no launcher option can hide
    another option or create a false positional operand boundary.
    """
    if index + 1 >= len(argv):
        _fail(path, "launcher option is missing its value")
    value = argv[index + 1]
    if value.startswith("-"):
        _fail(path, "launcher option value cannot be another option")
    if allowed is not None and value not in allowed:
        _fail(path, "launcher option value is invalid")
    return index + 2


SHELL_VALUE_OPTIONS = {"-o", "-O", "--rcfile", "--init-file"}
SHELL_SAFE_SHORT_CHARS = set("abefhlmnprtuvxBCEHPT")
SHELL_SAFE_LONG_OPTIONS = {
    "--debugger",
    "--help",
    "--login",
    "--noediting",
    "--noprofile",
    "--norc",
    "--noexec",
    "--posix",
    "--protected",
    "--restricted",
    "--verbose",
    "--version",
}


def _scan_posix_shell_prefix(argv: list[str], index: int, path: str) -> bool:
    self_contained = False
    while index < len(argv):
        token = argv[index]
        if token == "--":
            if index + 1 < len(argv):
                return argv[index + 1] != "-"
            return self_contained
        if not token.startswith("-"):
            return True
        if _has_short_command_switch(token) or token == "--command" or token.startswith("--command="):
            _fail(path, "shell command-string evaluation is forbidden")
        if token in SHELL_VALUE_OPTIONS:
            index = _consume_launcher_value(argv, index, path)
            continue
        if token.startswith("--"):
            if token not in SHELL_SAFE_LONG_OPTIONS:
                _fail(path, "unknown shell launcher option")
            if token in {"--help", "--version"}:
                self_contained = True
            index += 1
            continue
        if not all(character in SHELL_SAFE_SHORT_CHARS for character in token[1:]):
            _fail(path, "unknown shell launcher option")
        index += 1
    return self_contained


PYTHON_VALUE_OPTIONS = {"-W", "-X"}
PYTHON_NO_VALUE_OPTIONS = {
    "-B",
    "-E",
    "-I",
    "-O",
    "-OO",
    "-P",
    "-q",
    "-s",
    "-S",
    "-u",
    "-v",
    "-V",
    "-VV",
    "--dont-write-bytecode",
    "--help",
    "--ignore-environment",
    "--isolated",
    "--no-site",
    "--no-user-site",
    "--quiet",
    "--safe-path",
    "--utf8",
    "--version",
    "--warn-default-encoding",
}


def _scan_python_prefix(argv: list[str], index: int, path: str) -> bool:
    self_contained = False
    while index < len(argv):
        token = argv[index]
        if token == "--":
            if index + 1 < len(argv):
                return argv[index + 1] != "-"
            return self_contained
        if not token.startswith("-"):
            return True
        if token == "-c" or (token.startswith("-c") and not token.startswith("--")):
            _fail(path, "inline interpreter evaluation is forbidden")
        if token == "-m":
            index = _consume_launcher_value(argv, index, path)
            return True
        if token == "--check-hash-based-pycs":
            index = _consume_launcher_value(argv, index, path, allowed={"default", "always", "never"})
            continue
        if token.startswith("--check-hash-based-pycs="):
            _fail(path, "--check-hash-based-pycs requires a separate value")
        if token in PYTHON_VALUE_OPTIONS:
            index = _consume_launcher_value(argv, index, path)
            continue
        if token.startswith("-W") or token.startswith("-X"):
            index += 1
            continue
        if token in PYTHON_NO_VALUE_OPTIONS:
            if token in {"-V", "-VV", "--help", "--version"}:
                self_contained = True
            index += 1
            continue
        _fail(path, "unknown Python launcher option")
    return self_contained


NODE_VALUE_OPTIONS = {
    "-r",
    "--require",
    "--loader",
    "--import",
    "--experimental-loader",
    "-C",
    "--conditions",
    "--title",
    "--icu-data-dir",
    "--openssl-config",
    "--tls-cipher-list",
    "--max-http-header-size",
    "--redirect-warnings",
    "--trace-event-categories",
    "--test-name-pattern",
    "--test-reporter",
    "--test-reporter-destination",
    "--test-shard",
    "--inspect-port",
}

NODE_NO_VALUE_OPTIONS = {
    "-c",
    "-v",
    "--check",
    "--enable-source-maps",
    "--experimental-repl-await",
    "--help",
    "--no-addons",
    "--no-deprecation",
    "--no-warnings",
    "--pending-deprecation",
    "--preserve-symlinks",
    "--preserve-symlinks-main",
    "--test",
    "--test-only",
    "--throw-deprecation",
    "--trace-deprecation",
    "--trace-warnings",
    "--version",
    "--watch",
}


def _node_inline_switch(token: str) -> bool:
    return (
        token in {"-e", "-p", "--eval", "--print"}
        or (token.startswith("-e") and not token.startswith("--"))
        or (token.startswith("-p") and not token.startswith("--"))
        or token.startswith("--eval=")
        or token.startswith("--print=")
    )


def _scan_node_prefix(argv: list[str], index: int, path: str) -> bool:
    self_contained = False
    while index < len(argv):
        token = argv[index]
        if token == "--":
            if index + 1 < len(argv):
                return argv[index + 1] != "-"
            return self_contained
        if not token.startswith("-"):
            return True
        if _node_inline_switch(token):
            _fail(path, "inline interpreter evaluation is forbidden")
        if token in NODE_VALUE_OPTIONS:
            index = _consume_launcher_value(argv, index, path)
            continue
        if any(token.startswith(option + "=") for option in NODE_VALUE_OPTIONS if option.startswith("--")):
            index += 1
            continue
        if token in NODE_NO_VALUE_OPTIONS:
            if token in {"--test", "-v", "--help", "--version"}:
                self_contained = True
            index += 1
            continue
        _fail(path, "unknown Node launcher option")
    return self_contained


def _reject_shell_evaluation(argv: list[str], path: str) -> None:
    name, executable_index = _effective_executable(argv, path)
    if name == "env":
        _fail(path, "nested env prefixes are unsupported")
    prefix_start = executable_index + 1
    if name in UNSUPPORTED_LAUNCHERS:
        _fail(path, "launcher is unsupported on Linux")
    elif name in SHELL_NAMES:
        if not _scan_posix_shell_prefix(argv, prefix_start, path):
            _fail(path, "shell launcher requires a script operand or informational mode")
    elif name in PYTHON_NAMES:
        if not _scan_python_prefix(argv, prefix_start, path):
            _fail(path, "Python launcher requires a script, module, or informational mode")
    elif name in NODE_NAMES:
        if not _scan_node_prefix(argv, prefix_start, path):
            _fail(path, "Node launcher requires a script, test mode, or informational mode")


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


def _validate_generated(value: Any, rule_ids: set[str]) -> None:
    generated = _array(value, "generated", maximum=128)
    outputs: set[str] = set()
    for index, generated_rule in enumerate(generated):
        path = f"generated[{index}]"
        item = _exact_object(generated_rule, path, {"id", "inputs", "outputs", "argv", "timeout_seconds"})
        rule_id = _id(item["id"], f"{path}.id")
        if rule_id in rule_ids:
            _fail(f"{path}.id", "rule id must be globally unique")
        rule_ids.add(rule_id)
        inputs = _array(item["inputs"], f"{path}.inputs", minimum=1, maximum=256)
        _unique(inputs, f"{path}.inputs")
        for input_index, input_glob in enumerate(inputs):
            _relative_path(input_glob, f"{path}.inputs[{input_index}]")
        output_paths = _array(item["outputs"], f"{path}.outputs", minimum=1, maximum=256)
        _unique(output_paths, f"{path}.outputs")
        for output_index, output_path in enumerate(output_paths):
            normalized = _relative_path(output_path, f"{path}.outputs[{output_index}]", glob=False)
            if normalized in outputs:
                _fail(f"{path}.outputs[{output_index}]", "generated output path must be globally unique")
            outputs.add(normalized)
        _argv(item["argv"], f"{path}.argv")
        _reject_shell_evaluation(item["argv"], f"{path}.argv")
        _integer(item["timeout_seconds"], f"{path}.timeout_seconds", minimum=1, maximum=3600)


def _validate_rules(value: Any, rule_ids: set[str]) -> set[str]:
    rules = _array(value, "rules", maximum=128)
    command_ids: set[str] = set()
    for index, changed_rule in enumerate(rules):
        path = f"rules[{index}]"
        item = _exact_object(changed_rule, path, {"id", "paths", "prepare", "merge"})
        rule_id = _id(item["id"], f"{path}.id")
        if rule_id in rule_ids:
            _fail(f"{path}.id", "rule id must be globally unique")
        rule_ids.add(rule_id)
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
    rule_ids: set[str] = set()
    _validate_generated(root["generated"], rule_ids)
    command_ids = _validate_rules(root["rules"], rule_ids)
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
