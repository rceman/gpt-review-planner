#!/usr/bin/env python3
"""Validate the strict, dependency-free project-workflow.json contract."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class ProjectWorkflowError(ValueError):
    """Raised when a project workflow declaration is invalid."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProjectWorkflowError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    if path.is_symlink():
        raise ProjectWorkflowError("declaration path must not be a symlink")
    if not path.is_file():
        raise ProjectWorkflowError("declaration path must be a regular file")
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise ProjectWorkflowError("declaration must be UTF-8 JSON") from exc
    except OSError as exc:
        raise ProjectWorkflowError("cannot read declaration") from exc
    try:
        return json.loads(raw, object_pairs_hook=_strict_object)
    except json.JSONDecodeError as exc:
        raise ProjectWorkflowError(f"invalid JSON: {exc.msg}") from exc


def _exact_object(value: Any, label: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProjectWorkflowError(f"{label} must be an object")
    actual = set(value)
    missing = keys - actual
    unknown = actual - keys
    if missing:
        raise ProjectWorkflowError(f"{label} missing field(s): {', '.join(sorted(missing))}")
    if unknown:
        raise ProjectWorkflowError(f"{label} has unknown field(s): {', '.join(sorted(unknown))}")
    return value


def _constant(value: Any, expected: Any, label: str) -> None:
    if isinstance(expected, bool):
        valid = isinstance(value, bool) and value is expected
    else:
        valid = type(value) is type(expected) and value == expected
    if not valid:
        raise ProjectWorkflowError(f"{label} must be {expected!r}")


def _enum(value: Any, allowed: set[str], label: str) -> None:
    if not isinstance(value, str) or value not in allowed:
        raise ProjectWorkflowError(f"{label} must be one of: {', '.join(sorted(allowed))}")


def validate(value: Any) -> dict[str, Any]:
    root = _exact_object(value, "declaration", {"schema_version", "branching", "agent", "ci", "quality"})
    _constant(root["schema_version"], 1, "schema_version")

    branching = _exact_object(
        root["branching"],
        "branching",
        {
            "default_branch", "integration_branch", "task_branch_prefix",
            "one_active_task", "release_admission", "stale_task_policy", "revision_suffix",
        },
    )
    for key, expected in {
        "default_branch": "main",
        "integration_branch": "develop",
        "task_branch_prefix": "task/",
        "one_active_task": True,
        "release_admission": "merge_into_integration",
        "stale_task_policy": "new_revision_branch",
        "revision_suffix": "-r{revision}",
    }.items():
        _constant(branching[key], expected, f"branching.{key}")

    agent = _exact_object(
        root["agent"],
        "agent",
        {"completion_boundary", "wait_for_ci", "owns_merge", "owns_release", "owns_history_rewrite"},
    )
    for key, expected in {
        "completion_boundary": "pushed_task_commit",
        "wait_for_ci": False,
        "owns_merge": False,
        "owns_release": False,
        "owns_history_rewrite": False,
    }.items():
        _constant(agent[key], expected, f"agent.{key}")

    ci = _exact_object(root["ci"], "ci", {"task", "task_merge", "release"})
    for key in ("task", "task_merge", "release"):
        _enum(ci[key], {"disabled", "observe", "require"}, f"ci.{key}")

    quality = _exact_object(root["quality"], "quality", {"contract_path", "prepare_commit_required"})
    _constant(quality["contract_path"], "quality-gates.json", "quality.contract_path")
    if not isinstance(quality["contract_path"], str):
        raise ProjectWorkflowError("quality.contract_path must be a string")
    if (
        quality["contract_path"].startswith("/")
        or "\\" in quality["contract_path"]
        or any(part == ".." for part in Path(quality["contract_path"]).parts)
    ):
        raise ProjectWorkflowError("quality.contract_path must be a normalized relative POSIX path")
    _constant(quality["prepare_commit_required"], True, "quality.prepare_commit_required")
    return root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("declaration", type=Path)
    args = parser.parse_args(argv)
    try:
        validate(load_json(args.declaration))
    except (OSError, ProjectWorkflowError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {args.declaration}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
