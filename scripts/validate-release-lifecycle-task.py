#!/usr/bin/env python3
"""Validate exact release lifecycle declarations embedded in an immutable task."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
MODE_RE = re.compile(r"^Release lifecycle mode: (implementation_unreleased|release_publication)$")
TARGET_RE = re.compile(r"^Release target version: (.+)$")
REQUIRED_MODES = {"implementation_unreleased", "release_publication"}


class LifecycleError(ValueError):
    pass


def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LifecycleError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(strings(item))
        return result
    if isinstance(value, dict):
        result = []
        for key, item in value.items():
            result.extend(strings(key))
            result.extend(strings(item))
        return result
    return []


def validate_task(data: Any, require_release_surface: bool = True) -> dict[str, str]:
    if not isinstance(data, dict):
        raise LifecycleError("task must be a JSON object")
    all_strings = strings(data)
    mode_lines = [value for value in all_strings if MODE_RE.fullmatch(value)]
    target_lines = [value for value in all_strings if TARGET_RE.fullmatch(value)]
    if not require_release_surface and not mode_lines and not target_lines:
        return {"status": "not_applicable"}
    if len(mode_lines) != 1:
        raise LifecycleError("task must contain exactly one canonical release lifecycle mode declaration")
    if len(target_lines) != 1:
        raise LifecycleError("task must contain exactly one canonical release target declaration")
    mode = MODE_RE.fullmatch(mode_lines[0]).group(1)  # type: ignore[union-attr]
    target = TARGET_RE.fullmatch(target_lines[0]).group(1)  # type: ignore[union-attr]
    if mode not in REQUIRED_MODES:
        raise LifecycleError("unsupported release lifecycle mode")
    if not SEMVER_RE.fullmatch(target):
        raise LifecycleError(f"invalid release target version: {target!r}")
    gate_values: list[str] = []
    for key in ("required_gates", "task_required_gates", "gates", "required_commands"):
        value = data.get(key)
        if isinstance(value, list):
            gate_values.extend(item for item in value if isinstance(item, str))
    gate_text = "\n".join(gate_values)
    if mode == "implementation_unreleased":
        if "scripts/release.py check-source" not in gate_text:
            raise LifecycleError("implementation_unreleased requires the canonical check-source gate")
        if any(re.search(r"scripts/release\.py\s+(?:prepare|commit|tag)(?:\s|$)", item) for item in gate_values):
            raise LifecycleError("implementation_unreleased must not declare publication mutation commands")
    else:
        required = ("prepare", "check-release-ready", "commit", "check-tag-ready", "verify-tag")
        missing = [item for item in required if not any(f"release.py {item}" in gate for gate in gate_values)]
        if missing:
            raise LifecycleError("release_publication is missing lifecycle gates: " + ", ".join(missing))
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
