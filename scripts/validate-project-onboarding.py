#!/usr/bin/env python3
"""Validate the planner-owned project onboarding request and receipt formats.

The validator deliberately has no third-party dependencies.  JSON is parsed
with duplicate-key detection and the semantic checks below mirror the strict
contracts in the two onboarding schemas.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable


MAX_SAFE_INTEGER = 9007199254740991
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
OBJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
PROJECT_CODE = re.compile(r"^[A-Z]{3}$")
REMOTE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SESSION_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
WORKFLOW_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class ValidationError(ValueError):
    """Raised when an onboarding document violates its contract."""


def _duplicate_key_error(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: str | os.PathLike[str]) -> Any:
    """Load a regular UTF-8 JSON file and reject duplicate object keys."""

    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise ValidationError(f"JSON input is not a regular file: {candidate}")
    try:
        raw = candidate.read_bytes()
    except OSError as exc:
        raise ValidationError(f"cannot read {candidate}: {exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"JSON input is not UTF-8: {candidate}") from exc
    try:
        return json.loads(text, object_pairs_hook=_duplicate_key_error)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {candidate}: {exc.msg}") from exc


def _object(value: Any, name: str, required: Iterable[str], optional: Iterable[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be an object")
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - value.keys())
    unknown = sorted(set(value) - allowed)
    if missing:
        raise ValidationError(f"{name} missing required field(s): {', '.join(missing)}")
    if unknown:
        raise ValidationError(f"{name} has unknown field(s): {', '.join(unknown)}")
    return value


def _string(value: Any, name: str, *, minimum: int = 0, maximum: int | None = None) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string")
    if len(value) < minimum:
        raise ValidationError(f"{name} is shorter than {minimum} characters")
    if maximum is not None and len(value) > maximum:
        raise ValidationError(f"{name} is longer than {maximum} characters")
    return value


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{name} must be a boolean")
    return value


def _integer(value: Any, name: str) -> int:
    """Match JSON Schema integer semantics without accepting booleans."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be an integer")
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValidationError(f"{name} must be an integer")
    number = int(value)
    if number < 1 or number > MAX_SAFE_INTEGER:
        raise ValidationError(f"{name} must be between 1 and {MAX_SAFE_INTEGER}")
    return number


def _const(value: Any, expected: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must equal {expected}")
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        raise ValidationError(f"{name} must equal {expected}")
    if int(value) != expected:
        raise ValidationError(f"{name} must equal {expected}")


def _pattern(value: Any, expression: re.Pattern[str], name: str) -> str:
    text = _string(value, name)
    if expression.fullmatch(text) is None:
        raise ValidationError(f"{name} has an invalid format")
    return text


def _sha40(value: Any, name: str) -> str:
    return _pattern(value, SHA40, name)


def _sha256(value: Any, name: str) -> str:
    return _pattern(value, SHA256, name)


def _project_id(value: Any, name: str = "project_id") -> str:
    return _pattern(value, PROJECT_ID, name)


def _object_id(value: Any, name: str) -> str:
    return _pattern(value, OBJECT_ID, name)


def _project_code(value: Any, name: str = "project_code") -> str:
    return _pattern(value, PROJECT_CODE, name)


def _remote(value: Any, name: str = "remote") -> str:
    return _pattern(value, REMOTE, name)


def _session_key(value: Any, name: str = "session_key") -> str:
    return _pattern(value, SESSION_KEY, name)


def _absolute_path(value: Any, name: str) -> str:
    text = _string(value, name, minimum=2)
    if not os.path.isabs(text) or "\x00" in text or "\\" in text:
        raise ValidationError(f"{name} must be a normalized absolute POSIX path")
    parts = text.split("/")
    if not parts or parts[0] != "" or any(part in ("", ".", "..") for part in parts[1:]):
        raise ValidationError(f"{name} must be a normalized absolute POSIX path")
    if os.path.realpath(text) != text:
        raise ValidationError(f"{name} must not contain symlinked path components")
    return text


def _repository_url(value: Any, name: str = "repository_url") -> str:
    text = _string(value, name, minimum=1, maximum=2048)
    if any(char in text for char in "\x00\r\n"):
        raise ValidationError(f"{name} contains a forbidden control character")
    return text


def _branch(value: Any, name: str) -> str:
    text = _string(value, name, minimum=1, maximum=255)
    if (
        text.startswith("-")
        or ".." in text
        or text.endswith("/")
        or any(char in text for char in " ~^:?*[]\\\x00\r\n")
    ):
        raise ValidationError(f"{name} is not a safe Git ref component")
    return text


def _datetime(value: Any, name: str) -> str:
    text = _string(value, name, minimum=1)
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = _dt.datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(f"{name} must be RFC3339 date-time") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"{name} must include a timezone")
    if "T" not in text and "t" not in text:
        raise ValidationError(f"{name} must include a time separator")
    return text


def _relative_path(value: Any, name: str) -> str:
    text = _string(value, name, minimum=1, maximum=2048)
    parts = text.split("/")
    if (
        text.startswith("/")
        or "\\" in text
        or "\x00" in text
        or any(part in ("", ".", "..") for part in parts)
    ):
        raise ValidationError(f"{name} must be a normalized relative POSIX path")
    return text


def _unique_strings(values: Any, name: str, checker) -> list[str]:
    if not isinstance(values, list):
        raise ValidationError(f"{name} must be an array")
    if len(values) > 200:
        raise ValidationError(f"{name} may contain at most 200 entries")
    result = [checker(value, f"{name}[{index}]") for index, value in enumerate(values)]
    if len(set(result)) != len(result):
        raise ValidationError(f"{name} must contain unique identifiers")
    return result


def _validate_plan(plan: Any, project_id: str, name: str) -> None:
    value = _object(
        plan,
        name,
        ["schema_version", "project_id", "revision", "title", "summary", "current_objective", "queue", "sections", "updated_by", "updated_at"],
        ["active_task_id", "active_run_id"],
    )
    _const(value["schema_version"], 2, f"{name}.schema_version")
    if _project_id(value["project_id"], f"{name}.project_id") != project_id:
        raise ValidationError(f"{name}.project_id must match project_id")
    _integer(value["revision"], f"{name}.revision")
    _string(value["title"], f"{name}.title", minimum=1, maximum=300)
    _string(value["summary"], f"{name}.summary", minimum=1, maximum=500)
    objective = _string(value["current_objective"], f"{name}.current_objective", maximum=20000)
    if any(char in objective for char in "\x00"):
        raise ValidationError(f"{name}.current_objective contains NUL")
    _unique_strings(value["queue"], f"{name}.queue", _object_id)
    sections = value["sections"]
    if not isinstance(sections, list) or len(sections) > 200:
        raise ValidationError(f"{name}.sections must be an array of at most 200 entries")
    section_ids: list[str] = []
    for index, section in enumerate(sections):
        item = _object(section, f"{name}.sections[{index}]", ["id", "title", "short_description", "revision"], [])
        section_id = _object_id(item["id"], f"{name}.sections[{index}].id")
        section_ids.append(section_id)
        _string(item["title"], f"{name}.sections[{index}].title", minimum=1, maximum=300)
        short = _string(item["short_description"], f"{name}.sections[{index}].short_description", minimum=1, maximum=500)
        if any(char in short for char in "\x00\r\n"):
            raise ValidationError(f"{name}.sections[{index}].short_description contains a forbidden control character")
        _integer(item["revision"], f"{name}.sections[{index}].revision")
    if len(set(section_ids)) != len(section_ids):
        raise ValidationError(f"{name}.sections must contain unique identifiers")
    if "active_task_id" in value:
        _object_id(value["active_task_id"], f"{name}.active_task_id")
    if "active_run_id" in value:
        _object_id(value["active_run_id"], f"{name}.active_run_id")
    _string(value["updated_by"], f"{name}.updated_by", minimum=1, maximum=255)
    if any(char in value["updated_by"] for char in "\x00\r\n"):
        raise ValidationError(f"{name}.updated_by contains a forbidden control character")
    _datetime(value["updated_at"], f"{name}.updated_at")


def _validate_airelay(value: Any, name: str = "airelay") -> None:
    item = _object(value, name, ["session_required"], ["session_key"])
    required = _boolean(item["session_required"], f"{name}.session_required")
    if required:
        if "session_key" not in item:
            raise ValidationError(f"{name}.session_key is required")
        _session_key(item["session_key"], f"{name}.session_key")
    elif "session_key" in item:
        raise ValidationError(f"{name}.session_key is forbidden when session_required is false")


def _validate_workflow(value: Any, name: str = "workflow") -> None:
    item = _object(value, name, ["repository", "commit"], [])
    repository = _pattern(item["repository"], WORKFLOW_REPOSITORY, f"{name}.repository")
    if len(repository) > 255:
        raise ValidationError(f"{name}.repository is too long")
    _sha40(item["commit"], f"{name}.commit")


def validate_request(document: Any) -> dict[str, Any]:
    value = _object(
        document,
        "request",
        ["schema_version", "project_id", "root", "remote", "repository_url", "default_branch", "airelay", "initial_plan", "expected_hub_revision"],
        ["project_code", "workflow"],
    )
    _const(value["schema_version"], 1, "request.schema_version")
    project_id = _project_id(value["project_id"])
    _absolute_path(value["root"], "request.root")
    _remote(value["remote"])
    _repository_url(value["repository_url"])
    _branch(value["default_branch"], "request.default_branch")
    _validate_airelay(value["airelay"])
    if "project_code" in value:
        _project_code(value["project_code"])
    if "workflow" in value:
        _validate_workflow(value["workflow"])
    _validate_plan(value["initial_plan"], project_id, "request.initial_plan")
    _sha40(value["expected_hub_revision"], "request.expected_hub_revision")
    return value


def _validate_repository_proof(value: Any, project_id: str) -> None:
    item = _object(value, "receipt.repository_proof", ["root", "remote", "repository_url", "default_branch", "branch", "head"], [])
    _absolute_path(item["root"], "receipt.repository_proof.root")
    _remote(item["remote"], "receipt.repository_proof.remote")
    _repository_url(item["repository_url"], "receipt.repository_proof.repository_url")
    _branch(item["default_branch"], "receipt.repository_proof.default_branch")
    _branch(item["branch"], "receipt.repository_proof.branch")
    _sha40(item["head"], "receipt.repository_proof.head")


def _validate_session_proof(value: Any) -> None:
    item = _object(value, "receipt.session_proof", ["required", "status"], ["session_key", "controller_protocol_version"])
    required = _boolean(item["required"], "receipt.session_proof.required")
    status = _string(item["status"], "receipt.session_proof.status")
    if status not in {"active", "not_required", "unverified"}:
        raise ValidationError("receipt.session_proof.status is invalid")
    if required:
        if "session_key" not in item:
            raise ValidationError("receipt.session_proof.session_key is required")
        _session_key(item["session_key"], "receipt.session_proof.session_key")
        if status != "active":
            raise ValidationError("required session proof must be active")
    elif "session_key" in item:
        raise ValidationError("receipt.session_proof.session_key is forbidden when required is false")
    if "controller_protocol_version" in item:
        _integer(item["controller_protocol_version"], "receipt.session_proof.controller_protocol_version")


def _validate_timestamps(value: Any, state: str) -> None:
    item = _object(value, "receipt.timestamps", ["started_at", "updated_at"], ["prepared_at", "hub_committed_at", "activated_at", "rolled_back_at"])
    for key, timestamp in item.items():
        _datetime(timestamp, f"receipt.timestamps.{key}")
    if state == "prepared" and "prepared_at" not in item:
        raise ValidationError("prepared receipt requires timestamps.prepared_at")
    if state == "hub_committed" and "hub_committed_at" not in item:
        raise ValidationError("hub_committed receipt requires timestamps.hub_committed_at")
    if state == "activated" and not {"hub_committed_at", "activated_at"}.issubset(item):
        raise ValidationError("activated receipt requires hub_committed_at and activated_at")
    if state == "rolled_back" and "rolled_back_at" not in item:
        raise ValidationError("rolled_back receipt requires timestamps.rolled_back_at")


def _validate_created(value: Any, project_id: str, state: str) -> None:
    if state in {"prepared", "recovery_required"}:
        return
    project = _object(value.get("created_project"), "receipt.created_project", ["project_id", "repository_url", "default_branch", "status"], ["workflow_repository", "workflow_commit"])
    if _project_id(project["project_id"], "receipt.created_project.project_id") != project_id:
        raise ValidationError("receipt.created_project.project_id must match project_id")
    _repository_url(project["repository_url"], "receipt.created_project.repository_url")
    _branch(project["default_branch"], "receipt.created_project.default_branch")
    if project["status"] != "active":
        raise ValidationError("receipt.created_project.status must be active")
    if ("workflow_repository" in project) != ("workflow_commit" in project):
        raise ValidationError("created workflow repository and commit must be supplied together")
    if "workflow_repository" in project:
        _pattern(project["workflow_repository"], WORKFLOW_REPOSITORY, "receipt.created_project.workflow_repository")
        _sha40(project["workflow_commit"], "receipt.created_project.workflow_commit")
    plan = _object(value.get("created_plan"), "receipt.created_plan", ["schema_version", "project_id", "revision", "path"], [])
    _const(plan["schema_version"], 2, "receipt.created_plan.schema_version")
    if _project_id(plan["project_id"], "receipt.created_plan.project_id") != project_id:
        raise ValidationError("receipt.created_plan.project_id must match project_id")
    _integer(plan["revision"], "receipt.created_plan.revision")
    path = _relative_path(plan["path"], "receipt.created_plan.path")
    if path != f"gpt-tunnel/v1/projects/{project_id}/plan/current.json":
        raise ValidationError("receipt.created_plan.path is not the canonical current-plan path")
    identifiers = _object(value.get("created_identifiers"), "receipt.created_identifiers", ["schema_version", "project_id", "project_code", "next_task_number", "next_adr_number"], [])
    _const(identifiers["schema_version"], 1, "receipt.created_identifiers.schema_version")
    if _project_id(identifiers["project_id"], "receipt.created_identifiers.project_id") != project_id:
        raise ValidationError("receipt.created_identifiers.project_id must match project_id")
    _project_code(identifiers["project_code"], "receipt.created_identifiers.project_code")
    _integer(identifiers["next_task_number"], "receipt.created_identifiers.next_task_number")
    _integer(identifiers["next_adr_number"], "receipt.created_identifiers.next_adr_number")


def _validate_recovery(value: Any, state: str) -> None:
    item = _object(value, "receipt.recovery", ["status"], ["reason", "rolled_back_at"])
    status = _string(item["status"], "receipt.recovery.status")
    if status not in {"not_required", "required", "complete"}:
        raise ValidationError("receipt.recovery.status is invalid")
    if state in {"prepared", "hub_committed", "activated"} and status != "not_required":
        raise ValidationError("non-recovery receipt must have recovery.status=not_required")
    if state == "recovery_required":
        if status != "required" or "reason" not in item:
            raise ValidationError("recovery_required receipt needs required status and reason")
    if state == "rolled_back":
        if status != "complete" or "reason" not in item or "rolled_back_at" not in item:
            raise ValidationError("rolled_back receipt needs complete recovery proof")
    if "reason" in item:
        _string(item["reason"], "receipt.recovery.reason", minimum=1, maximum=2048)
    if "rolled_back_at" in item:
        _datetime(item["rolled_back_at"], "receipt.recovery.rolled_back_at")


def validate_receipt(document: Any) -> dict[str, Any]:
    value = _object(
        document,
        "receipt",
        ["schema_version", "operation_id", "request_sha256", "state", "project_id", "repository_proof", "worktree_proof", "session_proof", "registry_digests", "hub", "timestamps", "recovery"],
        ["created_project", "created_plan", "created_identifiers", "mirror_proof"],
    )
    _const(value["schema_version"], 1, "receipt.schema_version")
    _pattern(value["operation_id"], UUID, "receipt.operation_id")
    _sha256(value["request_sha256"], "receipt.request_sha256")
    state = _string(value["state"], "receipt.state")
    if state not in {"prepared", "hub_committed", "activated", "recovery_required", "rolled_back"}:
        raise ValidationError("receipt.state is invalid")
    project_id = _project_id(value["project_id"], "receipt.project_id")
    _validate_repository_proof(value["repository_proof"], project_id)
    worktree = _object(value["worktree_proof"], "receipt.worktree_proof", ["clean", "status_sha256"], [])
    _boolean(worktree["clean"], "receipt.worktree_proof.clean")
    _sha256(worktree["status_sha256"], "receipt.worktree_proof.status_sha256")
    _validate_session_proof(value["session_proof"])
    digests = _object(value["registry_digests"], "receipt.registry_digests", ["project_sha256", "plan_sha256", "identifiers_sha256"], [])
    for key in digests:
        _sha256(digests[key], f"receipt.registry_digests.{key}")
    hub = _object(value["hub"], "receipt.hub", ["before", "paths"], ["after"])
    _sha40(hub["before"], "receipt.hub.before")
    if state in {"hub_committed", "activated"} and "after" not in hub:
        raise ValidationError(f"{state} receipt requires receipt.hub.after")
    if state == "prepared" and "after" in hub:
        raise ValidationError("prepared receipt cannot contain receipt.hub.after")
    if "after" in hub:
        _sha40(hub["after"], "receipt.hub.after")
    paths = hub["paths"]
    if not isinstance(paths, list) or not paths:
        raise ValidationError("receipt.hub.paths must be a non-empty array")
    normalized_paths = [_relative_path(path, f"receipt.hub.paths[{index}]") for index, path in enumerate(paths)]
    if len(set(normalized_paths)) != len(normalized_paths):
        raise ValidationError("receipt.hub.paths must be unique")
    _validate_created(value, project_id, state)
    if state == "activated":
        mirror = _object(value.get("mirror_proof"), "receipt.mirror_proof", ["path", "repository_url", "head"], [])
        _absolute_path(mirror["path"], "receipt.mirror_proof.path")
        _repository_url(mirror["repository_url"], "receipt.mirror_proof.repository_url")
        _sha40(mirror["head"], "receipt.mirror_proof.head")
    elif "mirror_proof" in value:
        raise ValidationError("mirror_proof is allowed only for activated receipts")
    _validate_timestamps(value["timestamps"], state)
    _validate_recovery(value["recovery"], state)
    if state in {"hub_committed", "activated"}:
        for field in ("created_project", "created_plan", "created_identifiers"):
            if field not in value:
                raise ValidationError(f"{state} receipt requires {field}")
    if state in {"prepared", "recovery_required", "rolled_back"} and "mirror_proof" in value and state != "rolled_back":
        raise ValidationError(f"{state} receipt cannot contain mirror_proof")
    return value


def validate_file(path: str | os.PathLike[str], kind: str) -> dict[str, Any]:
    document = load_json(path)
    if kind == "request":
        return validate_request(document)
    if kind == "receipt":
        return validate_receipt(document)
    raise ValidationError(f"unknown document kind: {kind}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--request", metavar="PATH")
    group.add_argument("--receipt", metavar="PATH")
    args = parser.parse_args(argv)
    kind = "request" if args.request else "receipt"
    path = args.request or args.receipt
    try:
        validate_file(path, kind)
    except ValidationError as exc:
        print(f"INVALID {kind}: {exc}", file=sys.stderr)
        return 1
    print(f"VALID {kind}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
