#!/usr/bin/env python3
"""Validate release lifecycle declarations in the immutable task projection."""
from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any


SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MODE_RE = re.compile(r"^Release lifecycle mode: (implementation_unreleased|release_publication)$")
TARGET_RE = re.compile(r"^Release target version: (.+)$")
SHELL_OPERATOR_RE = re.compile(r"[;&|<>`]|\$\(|\$\{|\\\n")
SHELL_WRAPPERS = {
    "bash", "sh", "dash", "zsh", "ksh", "fish", "cmd", "powershell",
    "pwsh", "env", "sudo", "xargs", "echo", "printf", "true", "false",
}
RELEASE_COMMANDS = {
    "check",
    "check-source",
    "check-release-ready",
    "check-tag-ready",
    "prepare",
    "commit",
    "tag",
    "verify-tag",
}


class LifecycleError(ValueError):
    pass


def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LifecycleError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _string_array(data: dict[str, Any], field: str) -> list[str]:
    value = data.get(field)
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
        raise LifecycleError(f"{field} must be a non-empty array of strings")
    return value


def _declarations(constraints: list[str]) -> tuple[str, str]:
    mode_lines = [value for value in constraints if MODE_RE.fullmatch(value)]
    target_lines = [value for value in constraints if TARGET_RE.fullmatch(value)]
    if len(mode_lines) != 1:
        raise LifecycleError("constraints must contain exactly one canonical release lifecycle mode declaration")
    if len(target_lines) != 1:
        raise LifecycleError("constraints must contain exactly one canonical release target declaration")
    mode_match = MODE_RE.fullmatch(mode_lines[0])
    target_match = TARGET_RE.fullmatch(target_lines[0])
    assert mode_match is not None and target_match is not None
    mode = mode_match.group(1)
    target = target_match.group(1)
    if not SEMVER_RE.fullmatch(target):
        raise LifecycleError(f"invalid release target version: {target!r}")
    return mode, target


def _parse_gate(command: str, index: int) -> list[str]:
    if not command.strip():
        raise LifecycleError(f"required_gates[{index}] must not be empty")
    if SHELL_OPERATOR_RE.search(command):
        raise LifecycleError(f"required_gates[{index}] contains a shell operator or substitution")
    try:
        argv = shlex.split(command, posix=True)
    except ValueError as exc:
        raise LifecycleError(f"required_gates[{index}] is not valid shell-free argv: {exc}") from exc
    if not argv:
        raise LifecycleError(f"required_gates[{index}] must not be empty")
    if argv[0] in SHELL_WRAPPERS or "-c" in argv or "-Command" in argv or "/c" in argv:
        raise LifecycleError(f"required_gates[{index}] must not use a shell or command wrapper")
    return argv


def _is_script(argv: list[str], script: str) -> bool:
    return any(script in token for token in argv)


def _canonical_conformance(argv: list[str]) -> bool:
    return argv == [
        "python3",
        "scripts/validate-release-tool-conformance.py",
        "--release-script",
        "scripts/release.py",
        "--ci-script",
        "scripts/check-github-ci.py",
    ]


def _canonical_ci(argv: list[str]) -> bool:
    return (
        len(argv) == 11
        and argv[:2] == ["python3", "scripts/check-github-ci.py"]
        and argv[2] == "--repository"
        and bool(REPOSITORY_RE.fullmatch(argv[3]))
        and argv[4:] == ["--sha-from-git", "HEAD", "--policy", "required", "--wait", "--format", "json"]
    )


def _canonical_release(argv: list[str], command: str, target: str) -> bool:
    if command == "check-source":
        return argv == ["python3", "scripts/release.py", "check-source"]
    if command == "check-release-ready":
        return argv == ["python3", "scripts/release.py", "check-release-ready"]
    if command == "commit":
        return argv == ["python3", "scripts/release.py", "commit"]
    if command == "check-tag-ready":
        return argv == ["python3", "scripts/release.py", "check-tag-ready"]
    if command == "tag":
        return argv == ["python3", "scripts/release.py", "tag"]
    if command == "verify-tag":
        return argv == ["python3", "scripts/release.py", "verify-tag", f"v{target}"]
    if command == "prepare":
        return argv == ["python3", "scripts/release.py", "prepare", target]
    return False


def _reject_release_surface_spoof(argv: list[str], index: int) -> None:
    if _is_script(argv, "scripts/release.py"):
        raise LifecycleError(f"required_gates[{index}] contains a noncanonical release.py command")
    if _is_script(argv, "scripts/check-github-ci.py"):
        raise LifecycleError(f"required_gates[{index}] contains a noncanonical check-github-ci.py command")
    if _is_script(argv, "scripts/validate-release-tool-conformance.py"):
        raise LifecycleError(f"required_gates[{index}] contains a noncanonical release-tool conformance command")
    release_surface = {"VERSION", "CHANGELOG.md", "release-config.json"}
    if release_surface.intersection(argv):
        read_only = argv[0] == "git" and len(argv) > 1 and argv[1] in {"diff", "status", "show", "ls-files"}
        if not read_only:
            raise LifecycleError(f"required_gates[{index}] contains a manual release-surface mutation")


def _validate_implementation(gates: list[list[str]], target: str) -> None:
    conformance = [argv for argv in gates if _canonical_conformance(argv)]
    source = [argv for argv in gates if _canonical_release(argv, "check-source", target)]
    if len(conformance) != 1:
        raise LifecycleError("implementation_unreleased requires exactly one canonical two-script conformance gate")
    if len(source) != 1:
        raise LifecycleError("implementation_unreleased requires exactly one canonical check-source gate")
    seen_release: set[tuple[str, ...]] = set()
    for index, argv in enumerate(gates):
        if _canonical_conformance(argv) or _canonical_release(argv, "check-source", target):
            continue
        if argv == ["python3", "scripts/release.py", "check"]:
            key = tuple(argv)
            if key in seen_release:
                raise LifecycleError("duplicate canonical release consistency gate")
            seen_release.add(key)
            continue
        if _canonical_ci(argv):
            key = tuple(argv)
            if key in seen_release:
                raise LifecycleError("duplicate canonical CI gate")
            seen_release.add(key)
            continue
        _reject_release_surface_spoof(argv, index)


def _publication_kind(argv: list[str], target: str) -> str | None:
    ordered = (
        ("conformance", _canonical_conformance(argv)),
        ("prepare", _canonical_release(argv, "prepare", target)),
        ("check-release-ready", _canonical_release(argv, "check-release-ready", target)),
        ("commit", _canonical_release(argv, "commit", target)),
        ("ci", _canonical_ci(argv)),
        ("check-tag-ready", _canonical_release(argv, "check-tag-ready", target)),
        ("tag", _canonical_release(argv, "tag", target)),
        ("verify-tag", _canonical_release(argv, "verify-tag", target)),
    )
    for name, matches in ordered:
        if matches:
            return name
    return None


def _validate_publication(gates: list[list[str]], target: str) -> None:
    wanted = ["conformance", "prepare", "check-release-ready", "commit", "ci", "check-tag-ready", "tag", "verify-tag"]
    found: list[tuple[int, str]] = []
    for index, argv in enumerate(gates):
        kind = _publication_kind(argv, target)
        if kind is not None:
            found.append((index, kind))
            continue
        _reject_release_surface_spoof(argv, index)
    names = [kind for _, kind in found]
    if names != wanted:
        raise LifecycleError(
            "release_publication requires the exact ordered canonical gate sequence: "
            + ", ".join(wanted)
        )
    if [index for index, _ in found] != sorted(index for index, _ in found):
        raise LifecycleError("release_publication canonical gates are out of order")
    first = found[0][0]
    last = found[-1][0]
    if any(index < first or index > last for index in range(len(gates)) if index not in {item[0] for item in found}):
        raise LifecycleError("release_publication allows unrelated quality gates only between canonical lifecycle gates")


def validate_task(data: Any, require_release_surface: bool = True) -> dict[str, str]:
    if not isinstance(data, dict):
        raise LifecycleError("task must be a JSON object")
    constraints = _string_array(data, "constraints")
    raw_gates = _string_array(data, "required_gates")
    mode_lines = [value for value in constraints if MODE_RE.fullmatch(value)]
    target_lines = [value for value in constraints if TARGET_RE.fullmatch(value)]
    if not require_release_surface and not mode_lines and not target_lines:
        return {"status": "not_applicable"}
    mode, target = _declarations(constraints)
    gates = [_parse_gate(command, index) for index, command in enumerate(raw_gates)]
    if mode == "implementation_unreleased":
        _validate_implementation(gates, target)
    else:
        _validate_publication(gates, target)
    return {"status": "valid", "lifecycle_mode": mode, "target_version": target}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", type=Path)
    parser.add_argument("--not-release-touching", action="store_true")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.task.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)
        result = validate_task(data, require_release_surface=not args.not_release_touching)
    except (OSError, UnicodeError, json.JSONDecodeError, LifecycleError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("PASS: " + json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
