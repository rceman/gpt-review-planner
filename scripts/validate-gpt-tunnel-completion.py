#!/usr/bin/env python3
"""Validate the single-authority GPT Tunnel completion document."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
GATE_ID_RE = re.compile(r"^G([1-9][0-9]*)$")
AC_ID_RE = re.compile(r"^AC([1-9][0-9]*)$")
STATUSES = {"succeeded", "failed", "needs_gpt_revision"}
MAX_ITEMS = 128
MAX_TEXT = 2048


class DuplicateKey(ValueError):
    pass


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKey(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)


def _bounded_strings(value: Any, field: str, errors: list[str], limit: int = 64) -> None:
    if not isinstance(value, list) or len(value) > limit:
        errors.append(f"{field} must be an array of at most {limit} strings")
        return
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip() or len(item.encode("utf-8")) > MAX_TEXT:
            errors.append(f"{field}[{index}] must be a bounded non-empty string")


def validate_value(
    value: Any,
    *,
    expected_run_id: str | None = None,
    expected_task_sha256: str | None = None,
    gate_count: int | None = None,
    acceptance_count: int | None = None,
) -> list[str]:
    errors: list[str] = []
    allowed = {
        "schema_version", "run_id", "task_sha256", "status", "summary",
        "gate_results", "acceptance_coverage", "deviations", "remaining_risks",
    }
    if not isinstance(value, dict):
        return ["completion root must be an object"]
    unknown = sorted(set(value) - allowed)
    errors.extend(f"unknown field: {key}" for key in unknown)
    if value.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    run_id = value.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        errors.append("run_id must be a normalized non-empty identifier")
    elif expected_run_id is not None and run_id != expected_run_id:
        errors.append("run_id does not match expected run ID")
    task_sha = value.get("task_sha256")
    if not isinstance(task_sha, str) or not SHA256_RE.fullmatch(task_sha):
        errors.append("task_sha256 must be a lowercase 64-character SHA-256")
    elif expected_task_sha256 is not None and task_sha != expected_task_sha256:
        errors.append("task_sha256 does not match expected task SHA-256")
    status = value.get("status")
    if status not in STATUSES:
        errors.append("status must be succeeded, failed, or needs_gpt_revision")
    summary = value.get("summary")
    if not isinstance(summary, str) or not summary.strip() or len(summary.encode("utf-8")) > 4096:
        errors.append("summary must be a bounded non-empty string")

    gates = value.get("gate_results")
    if not isinstance(gates, list) or len(gates) > MAX_ITEMS:
        errors.append("gate_results must be an array of at most 128 entries")
        gates = []
    gate_ids: list[str] = []
    for index, item in enumerate(gates):
        if not isinstance(item, dict) or set(item) != {"id", "exit_code"}:
            errors.append(f"gate_results[{index}] must contain exactly id and exit_code")
            continue
        gate_id = item["id"]
        if not isinstance(gate_id, str) or not GATE_ID_RE.fullmatch(gate_id):
            errors.append(f"gate_results[{index}].id is invalid")
        elif gate_id in gate_ids:
            errors.append(f"duplicate gate result: {gate_id}")
        gate_ids.append(gate_id)
        exit_code = item["exit_code"]
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            errors.append(f"gate_results[{index}].exit_code is invalid")

    coverage = value.get("acceptance_coverage")
    if not isinstance(coverage, list) or len(coverage) > MAX_ITEMS:
        errors.append("acceptance_coverage must be an array of at most 128 entries")
        coverage = []
    coverage_ids: list[str] = []
    for index, item in enumerate(coverage):
        if not isinstance(item, str) or not AC_ID_RE.fullmatch(item):
            errors.append(f"acceptance_coverage[{index}] is invalid")
        elif item in coverage_ids:
            errors.append(f"duplicate acceptance coverage: {item}")
        if isinstance(item, str) and AC_ID_RE.fullmatch(item):
            coverage_ids.append(item)

    _bounded_strings(value.get("deviations"), "deviations", errors)
    _bounded_strings(value.get("remaining_risks"), "remaining_risks", errors)

    if gate_count is not None and (gate_count < 0 or gate_count > MAX_ITEMS):
        errors.append("gate_count is outside the supported range")
    if acceptance_count is not None and (acceptance_count < 0 or acceptance_count > MAX_ITEMS):
        errors.append("acceptance_count is outside the supported range")

    expected_gates = gate_count if gate_count is not None else None
    expected_acceptance = acceptance_count if acceptance_count is not None else None
    if status == "succeeded":
        if expected_gates is None or expected_acceptance is None:
            errors.append("succeeded validation requires gate_count and acceptance_count")
        else:
            wanted_gates = [f"G{i}" for i in range(1, expected_gates + 1)]
            wanted_ac = [f"AC{i}" for i in range(1, expected_acceptance + 1)]
            if gate_ids != wanted_gates:
                errors.append("succeeded gate_results must be the complete ordered G1..Gn set")
            if coverage_ids != wanted_ac:
                errors.append("succeeded acceptance_coverage must be the complete ordered AC1..ACn set")
            if any(item.get("exit_code") != 0 for item in gates if isinstance(item, dict)):
                errors.append("succeeded gate_results must all have exit_code 0")
    elif status in {"failed", "needs_gpt_revision"}:
        if expected_gates is not None:
            prefix = [f"G{i}" for i in range(1, len(gate_ids) + 1)]
            if gate_ids != prefix or len(gate_ids) > expected_gates:
                errors.append("non-success gate_results must be an ordered executed prefix")
        if expected_acceptance is not None:
            numeric = [int(item[2:]) for item in coverage_ids]
            if any(number > expected_acceptance for number in numeric) or numeric != sorted(numeric):
                errors.append("non-success acceptance_coverage must be an ordered task subset")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("completion", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--task-sha256")
    parser.add_argument("--gate-count", type=int)
    parser.add_argument("--acceptance-count", type=int)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    errors: list[str] = []
    try:
        value = load_json(args.completion)
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKey) as exc:
        errors.append(f"invalid completion JSON: {exc}")
        value = None
    if value is not None:
        errors.extend(validate_value(value, expected_run_id=args.run_id,
                                     expected_task_sha256=args.task_sha256,
                                     gate_count=args.gate_count,
                                     acceptance_count=args.acceptance_count))
    if args.format == "json":
        print(json.dumps({"schema_version": 1, "valid": not errors, "errors": errors},
                         sort_keys=True, separators=(",", ":")))
    elif errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
    else:
        print(f"PASS: {args.completion}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
