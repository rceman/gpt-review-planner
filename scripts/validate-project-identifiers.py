#!/usr/bin/env python3
"""Validate durable project allocation records and canonical compact IDs."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
PROJECT_CODE_RE = re.compile(r"^[A-Z]{3}$")
TASK_RE = re.compile(r"^(?P<code>[A-Z]{3})-TSK(?P<number>[1-9][0-9]*)$")
RUN_RE = re.compile(r"^(?P<task>[A-Z]{3}-TSK[1-9][0-9]*)-RUN(?P<number>[1-9][0-9]*)$")
ADR_RE = re.compile(r"^(?P<code>[A-Z]{3})-ADR(?P<number>[1-9][0-9]*)$")
MAX_IDENTIFIER_NUMBER = 9007199254740991
MAX_IDENTIFIER_NUMBER_TEXT = str(MAX_IDENTIFIER_NUMBER)


class ProjectIdentifiersError(ValueError):
    """Raised when an allocation record or compact ID is invalid."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProjectIdentifiersError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    if path.is_symlink():
        raise ProjectIdentifiersError("declaration path must not be a symlink")
    if not path.is_file():
        raise ProjectIdentifiersError("declaration path must be a regular file")
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise ProjectIdentifiersError("declaration must be UTF-8 JSON") from exc
    except OSError as exc:
        raise ProjectIdentifiersError("cannot read declaration") from exc
    try:
        return json.loads(raw, object_pairs_hook=_strict_object)
    except json.JSONDecodeError as exc:
        raise ProjectIdentifiersError(f"invalid JSON: {exc.msg}") from exc


def _exact_object(value: Any, label: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProjectIdentifiersError(f"{label} must be an object")
    actual = set(value)
    missing = keys - actual
    unknown = actual - keys
    if missing:
        raise ProjectIdentifiersError(f"{label} missing field(s): {', '.join(sorted(missing))}")
    if unknown:
        raise ProjectIdentifiersError(f"{label} has unknown field(s): {', '.join(sorted(unknown))}")
    return value


def _json_integer(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float):
        return math.isfinite(value) and value.is_integer()
    return True


def _constant(value: Any, expected: Any, label: str, *, json_number: bool = False) -> None:
    if isinstance(expected, bool):
        valid = isinstance(value, bool) and value is expected
    elif json_number and isinstance(value, (int, float)) and not isinstance(value, bool):
        valid = value == expected
    else:
        valid = type(value) is type(expected) and value == expected
    if not valid:
        raise ProjectIdentifiersError(f"{label} must be {expected!r}")


def _counter(value: Any, label: str) -> None:
    if not _json_integer(value) or value < 1 or value > MAX_IDENTIFIER_NUMBER:
        raise ProjectIdentifiersError(f"{label} must be a positive integer")


def _number(text: str, label: str) -> int:
    if len(text) > len(MAX_IDENTIFIER_NUMBER_TEXT) or (
        len(text) == len(MAX_IDENTIFIER_NUMBER_TEXT) and text > MAX_IDENTIFIER_NUMBER_TEXT
    ):
        raise ProjectIdentifiersError(f"{label} exceeds the maximum {MAX_IDENTIFIER_NUMBER}")
    return int(text)


def validate_project_identifiers(
    value: Any,
    *,
    expected_project_id: str | None = None,
    expected_project_code: str | None = None,
) -> dict[str, Any]:
    """Validate and return one allocation record.

    Expected values are optional adoption bindings. Once supplied by a project,
    they make a changed project identity or code fail closed.
    """
    record = _exact_object(
        value,
        "project identifiers",
        {"schema_version", "project_id", "project_code", "next_task_number", "next_adr_number"},
    )
    _constant(record["schema_version"], 1, "schema_version", json_number=True)
    project_id = record["project_id"]
    if (
        not isinstance(project_id, str)
        or len(project_id) > 64
        or PROJECT_ID_RE.fullmatch(project_id) is None
    ):
        raise ProjectIdentifiersError("project_id must be a canonical lowercase gateway identifier")
    project_code = record["project_code"]
    if not isinstance(project_code, str) or PROJECT_CODE_RE.fullmatch(project_code) is None:
        raise ProjectIdentifiersError("project_code must be exactly three uppercase ASCII letters")
    _counter(record["next_task_number"], "next_task_number")
    _counter(record["next_adr_number"], "next_adr_number")
    if expected_project_id is not None and project_id != expected_project_id:
        raise ProjectIdentifiersError("project_id does not match the immutable adoption binding")
    if expected_project_code is not None and project_code != expected_project_code:
        raise ProjectIdentifiersError("project_code does not match the immutable adoption binding")
    return record


def validate(value: Any, **kwargs: Any) -> dict[str, Any]:
    """Compatibility-free short alias for the canonical record validator."""
    return validate_project_identifiers(value, **kwargs)


def _check_code(code: str, expected_project_code: str | None) -> None:
    if expected_project_code is not None and code != expected_project_code:
        raise ProjectIdentifiersError("identifier project code does not match the allocation record")


def parse_task_id(identifier: str, project_code: str | None = None) -> dict[str, Any]:
    if not isinstance(identifier, str):
        raise ProjectIdentifiersError("task ID must be a string")
    match = TASK_RE.fullmatch(identifier)
    if match is None:
        raise ProjectIdentifiersError("task ID must match <CODE>-TSK<N> with no leading zero")
    code = match.group("code")
    _check_code(code, project_code)
    return {"identifier": identifier, "code": code, "number": _number(match.group("number"), "task number")}


def validate_task_id(identifier: str, project_code: str | None = None) -> dict[str, Any]:
    return parse_task_id(identifier, project_code)


def parse_run_id(identifier: str, project_code: str | None = None) -> dict[str, Any]:
    if not isinstance(identifier, str):
        raise ProjectIdentifiersError("run ID must be a string")
    match = RUN_RE.fullmatch(identifier)
    if match is None:
        raise ProjectIdentifiersError("run ID must match <TASK-ID>-RUN<N> with no leading zero")
    task = parse_task_id(match.group("task"), project_code)
    return {
        "identifier": identifier,
        "code": task["code"],
        "task_id": task["identifier"],
        "task_number": task["number"],
        "run_number": _number(match.group("number"), "run number"),
    }


def validate_run_id(identifier: str, project_code: str | None = None) -> dict[str, Any]:
    return parse_run_id(identifier, project_code)


def parse_adr_id(identifier: str, project_code: str | None = None) -> dict[str, Any]:
    if not isinstance(identifier, str):
        raise ProjectIdentifiersError("ADR ID must be a string")
    match = ADR_RE.fullmatch(identifier)
    if match is None:
        raise ProjectIdentifiersError("ADR ID must match <CODE>-ADR<N> with no leading zero")
    code = match.group("code")
    _check_code(code, project_code)
    return {"identifier": identifier, "code": code, "number": _number(match.group("number"), "ADR number")}


def validate_adr_id(identifier: str, project_code: str | None = None) -> dict[str, Any]:
    return parse_adr_id(identifier, project_code)


def task_branch_name(task_id: str, slug: str, project_code: str | None = None) -> str:
    parse_task_id(task_id, project_code)
    if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ProjectIdentifiersError("task branch slug must be a normalized lowercase slug")
    return f"task/{task_id}-{slug}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("declaration", type=Path)
    args = parser.parse_args(argv)
    try:
        validate_project_identifiers(load_json(args.declaration))
    except (OSError, ProjectIdentifiersError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {args.declaration}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
