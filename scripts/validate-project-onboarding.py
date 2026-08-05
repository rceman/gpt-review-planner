#!/usr/bin/env python3
"""Validate the strict planner-owned project onboarding contract."""

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
SESSION_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
WORKFLOW_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ABSOLUTE_PATH = re.compile(r"^/(?!.*(?:^|/)\.\.?(?:/|$))(?!.*//)[^\\\x00]+$")

STATES = {"prepared", "hub_committed", "activated", "recovery_required", "rolled_back"}
COMPLETED_STATES = {"prepared", "hub_committed", "activated"}
RECOVERY_STATUSES = {"not_required", "required", "complete"}


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
        text = raw.decode("utf-8")
        return json.loads(text, object_pairs_hook=_duplicate_key_error)
    except UnicodeDecodeError as exc:
        raise ValidationError(f"JSON input is not UTF-8: {candidate}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {candidate}: {exc.msg}") from exc
    except OSError as exc:
        raise ValidationError(f"cannot read {candidate}: {exc}") from exc


def _object(value: Any, name: str, required: Iterable[str], optional: Iterable[str] = ()) -> dict[str, Any]:
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


def _string(value: Any, name: str, minimum: int = 0, maximum: int | None = None) -> str:
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
    """Implement JSON Schema integer semantics without accepting booleans."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be an integer")
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
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
    if not ABSOLUTE_PATH.fullmatch(text) or any(ord(char) < 32 or ord(char) == 127 for char in text) or os.path.realpath(text) != text:
        raise ValidationError(f"{name} must be a normalized absolute POSIX path")
    return text


def _repository_url(value: Any, name: str = "repository_url") -> str:
    text = _string(value, name, minimum=1, maximum=2048)
    if text != text.strip() or any(ord(char) < 32 or ord(char) == 127 for char in text):
        raise ValidationError(f"{name} contains surrounding whitespace or control characters")
    if text.startswith("/"):
        _absolute_path(text, name)
    else:
        before, separator, after = text.partition(":")
        if not separator or not before or not after or any(char.isspace() for char in text):
            raise ValidationError(f"{name} must be an absolute path or a Git URL containing ':'")
    return text


def _branch(value: Any, name: str) -> str:
    text = _string(value, name, minimum=1, maximum=255)
    if text.startswith("-") or ".." in text or text.endswith("/") or any(char in text for char in " ~^:?*[]\\\x00\r\n"):
        raise ValidationError(f"{name} is not a safe Git ref component")
    return text


def _parse_datetime(value: Any, name: str) -> tuple[str, _dt.datetime]:
    text = _string(value, name, minimum=1)
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = _dt.datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValidationError(f"{name} must be RFC3339 date-time") from exc
    if parsed.tzinfo is None or ("T" not in text and "t" not in text):
        raise ValidationError(f"{name} must include a timezone and time separator")
    return text, parsed


def _datetime(value: Any, name: str) -> str:
    return _parse_datetime(value, name)[0]


def _relative_path(value: Any, name: str) -> str:
    text = _string(value, name, minimum=1, maximum=2048)
    parts = text.split("/")
    if text.startswith("/") or "\\" in text or any(ord(char) < 32 or ord(char) == 127 for char in text) or any(part in ("", ".", "..") for part in parts):
        raise ValidationError(f"{name} must be a normalized relative POSIX path")
    return text


def _unique(values: Any, name: str, checker, maximum: int = 200) -> list[str]:
    if not isinstance(values, list) or len(values) > maximum:
        raise ValidationError(f"{name} must be an array of at most {maximum} entries")
    result = [checker(value, f"{name}[{index}]") for index, value in enumerate(values)]
    if len(set(result)) != len(result):
        raise ValidationError(f"{name} must contain unique values")
    return result


def _validate_plan(plan: Any, project_id: str, name: str) -> None:
    value = _object(
        plan,
        name,
        ["schema_version", "project_id", "revision", "title", "summary", "current_objective", "queue", "sections", "updated_by", "updated_at"],
        [],
    )
    _const(value["schema_version"], 2, f"{name}.schema_version")
    if _project_id(value["project_id"], f"{name}.project_id") != project_id:
        raise ValidationError(f"{name}.project_id must match project_id")
    _integer(value["revision"], f"{name}.revision")
    _string(value["title"], f"{name}.title", 1, 300)
    _string(value["summary"], f"{name}.summary", 1, 500)
    objective = _string(value["current_objective"], f"{name}.current_objective", maximum=20000)
    if "\x00" in objective:
        raise ValidationError(f"{name}.current_objective contains NUL")
    _unique(value["queue"], f"{name}.queue", _object_id)
    sections = value["sections"]
    if not isinstance(sections, list) or len(sections) > 200:
        raise ValidationError(f"{name}.sections must be an array of at most 200 entries")
    section_ids: list[str] = []
    for index, section in enumerate(sections):
        item = _object(section, f"{name}.sections[{index}]", ["id", "title", "short_description", "revision"])
        section_ids.append(_object_id(item["id"], f"{name}.sections[{index}].id"))
        _string(item["title"], f"{name}.sections[{index}].title", 1, 300)
        short = _string(item["short_description"], f"{name}.sections[{index}].short_description", 1, 500)
        if any(char in short for char in "\x00\r\n"):
            raise ValidationError(f"{name}.sections[{index}].short_description contains a forbidden control character")
        _integer(item["revision"], f"{name}.sections[{index}].revision")
    if len(set(section_ids)) != len(section_ids):
        raise ValidationError(f"{name}.sections must contain unique identifiers")
    if "active_task_id" in value:
        raise ValidationError(f"{name}.active_task_id is forbidden for an onboarding plan")
    if "active_run_id" in value:
        raise ValidationError(f"{name}.active_run_id is forbidden for an onboarding plan")
    updated_by = _string(value["updated_by"], f"{name}.updated_by", 1, 255)
    if any(char in updated_by for char in "\x00\r\n"):
        raise ValidationError(f"{name}.updated_by contains a forbidden control character")
    _datetime(value["updated_at"], f"{name}.updated_at")


def _validate_airelay(value: Any) -> None:
    item = _object(value, "request.airelay", ["session_required"], ["session_key"])
    required = _boolean(item["session_required"], "request.airelay.session_required")
    if required:
        if "session_key" not in item:
            raise ValidationError("request.airelay.session_key is required")
        _session_key(item["session_key"], "request.airelay.session_key")
    elif "session_key" in item:
        raise ValidationError("request.airelay.session_key is forbidden when session_required is false")


def _validate_workflow(value: Any) -> None:
    item = _object(value, "request.workflow", ["repository", "commit"])
    repository = _pattern(item["repository"], WORKFLOW_REPOSITORY, "request.workflow.repository")
    if len(repository) > 255:
        raise ValidationError("request.workflow.repository is too long")
    _sha40(item["commit"], "request.workflow.commit")


def validate_request(document: Any) -> dict[str, Any]:
    value = _object(
        document,
        "request",
        ["schema_version", "project_id", "root", "remote", "repository_url", "default_branch", "airelay", "project_code", "gateway_state_dir", "initial_plan", "expected_hub_revision"],
        ["workflow"],
    )
    _const(value["schema_version"], 1, "request.schema_version")
    project_id = _project_id(value["project_id"])
    _absolute_path(value["root"], "request.root")
    _remote(value["remote"])
    _repository_url(value["repository_url"])
    _branch(value["default_branch"], "request.default_branch")
    _validate_airelay(value["airelay"])
    _project_code(value["project_code"])
    _absolute_path(value["gateway_state_dir"], "request.gateway_state_dir")
    if "workflow" in value:
        _validate_workflow(value["workflow"])
    _validate_plan(value["initial_plan"], project_id, "request.initial_plan")
    _sha40(value["expected_hub_revision"], "request.expected_hub_revision")
    return value


def _validate_repository_proof(value: Any, project_id: str) -> dict[str, Any]:
    item = _object(value, "receipt.repository_proof", ["root", "remote", "repository_url", "default_branch", "branch", "head", "gateway_state_dir"])
    _absolute_path(item["root"], "receipt.repository_proof.root")
    _remote(item["remote"], "receipt.repository_proof.remote")
    _repository_url(item["repository_url"], "receipt.repository_proof.repository_url")
    _branch(item["default_branch"], "receipt.repository_proof.default_branch")
    _branch(item["branch"], "receipt.repository_proof.branch")
    _sha40(item["head"], "receipt.repository_proof.head")
    _absolute_path(item["gateway_state_dir"], "receipt.repository_proof.gateway_state_dir")
    return item


def _validate_session_proof(value: Any) -> None:
    item = _object(value, "receipt.session_proof", ["required", "status"], ["session_key", "controller_protocol_version"])
    required = _boolean(item["required"], "receipt.session_proof.required")
    status = _string(item["status"], "receipt.session_proof.status")
    if required:
        if "session_key" not in item or status != "active":
            raise ValidationError("required session proof needs session_key and active status")
        _session_key(item["session_key"], "receipt.session_proof.session_key")
        if "controller_protocol_version" in item:
            _integer(item["controller_protocol_version"], "receipt.session_proof.controller_protocol_version")
    else:
        if status != "not_required" or "session_key" in item or "controller_protocol_version" in item:
            raise ValidationError("optional session proof must be not_required without session fields")


def _canonical_hub_paths(project_id: str) -> set[str]:
    prefix = f"gpt-tunnel/v1/projects/{project_id}"
    return {f"{prefix}/project.json", f"{prefix}/plan/current.json", f"{prefix}/identifiers.json"}


def _validate_hub_paths(value: Any, project_id: str, name: str) -> None:
    if not isinstance(value, list) or len(value) != 3:
        raise ValidationError(f"{name} must contain exactly three canonical paths")
    paths = [_relative_path(item, f"{name}[{index}]") for index, item in enumerate(value)]
    if len(set(paths)) != len(paths) or set(paths) != _canonical_hub_paths(project_id):
        raise ValidationError(f"{name} must equal the canonical project/plan/identifiers path set")


def _validate_created_records(value: dict[str, Any], project_id: str, effective_state: str) -> None:
    fields = {"created_project", "created_plan", "created_identifiers"}
    present = fields & value.keys()
    if effective_state == "prepared":
        if present:
            raise ValidationError("prepared state cannot contain created hub records")
        return
    if present != fields:
        raise ValidationError(f"{effective_state} state requires all created hub records")
    project = _object(value["created_project"], "receipt.created_project", ["project_id", "repository_url", "default_branch", "status"], ["workflow_repository", "workflow_commit"])
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
    plan = _object(value["created_plan"], "receipt.created_plan", ["schema_version", "project_id", "revision", "path"])
    _const(plan["schema_version"], 2, "receipt.created_plan.schema_version")
    if _project_id(plan["project_id"], "receipt.created_plan.project_id") != project_id:
        raise ValidationError("receipt.created_plan.project_id must match project_id")
    _integer(plan["revision"], "receipt.created_plan.revision")
    if _relative_path(plan["path"], "receipt.created_plan.path") != f"gpt-tunnel/v1/projects/{project_id}/plan/current.json":
        raise ValidationError("receipt.created_plan.path is not canonical")
    identifiers = _object(value["created_identifiers"], "receipt.created_identifiers", ["schema_version", "project_id", "project_code", "next_task_number", "next_adr_number"])
    _const(identifiers["schema_version"], 1, "receipt.created_identifiers.schema_version")
    if _project_id(identifiers["project_id"], "receipt.created_identifiers.project_id") != project_id:
        raise ValidationError("receipt.created_identifiers.project_id must match project_id")
    _project_code(identifiers["project_code"], "receipt.created_identifiers.project_code")
    _integer(identifiers["next_task_number"], "receipt.created_identifiers.next_task_number")
    _integer(identifiers["next_adr_number"], "receipt.created_identifiers.next_adr_number")


def _validate_registry_digests(value: Any) -> None:
    item = _object(value, "receipt.registry_digests", ["managed_before_sha256", "managed_after_sha256", "project_sha256", "plan_sha256", "identifiers_sha256"])
    for key, digest in item.items():
        _sha256(digest, f"receipt.registry_digests.{key}")
    if item["managed_before_sha256"] == item["managed_after_sha256"]:
        raise ValidationError("managed registry before and after digests must differ")


def _validate_timestamps(value: Any, state: str, effective_state: str) -> dict[str, _dt.datetime]:
    item = _object(value, "receipt.timestamps", ["started_at", "updated_at"], ["prepared_at", "hub_committed_at", "activated_at", "rolled_back_at"])
    parsed: dict[str, _dt.datetime] = {}
    for key, timestamp in item.items():
        parsed[key] = _parse_datetime(timestamp, f"receipt.timestamps.{key}")[1]
    required_by_state = {
        "prepared": {"prepared_at"},
        "hub_committed": {"prepared_at", "hub_committed_at"},
        "activated": {"prepared_at", "hub_committed_at", "activated_at"},
    }
    if not required_by_state[effective_state].issubset(item):
        raise ValidationError(f"{effective_state} proof is missing a required phase timestamp")
    forbidden_by_state = {
        "prepared": {"hub_committed_at", "activated_at"},
        "hub_committed": {"activated_at"},
        "activated": set(),
    }
    forbidden = forbidden_by_state[effective_state] | ({"rolled_back_at"} if state != "rolled_back" else set())
    if forbidden & item.keys():
        raise ValidationError(f"receipt timestamps contain fields beyond the completed state: {', '.join(sorted(forbidden & item.keys()))}")
    phase_order = ["started_at", "prepared_at", "hub_committed_at", "activated_at", "rolled_back_at"]
    previous: _dt.datetime | None = None
    for key in phase_order:
        if key in parsed:
            if previous is not None and parsed[key] < previous:
                raise ValidationError("receipt timestamps are not chronological")
            previous = parsed[key]
    if parsed["updated_at"] < previous if previous is not None else False:
        raise ValidationError("receipt.timestamps.updated_at precedes the last phase")
    if state != "rolled_back" and "rolled_back_at" in item:
        raise ValidationError("rolled_back_at is allowed only for rolled_back receipts")
    if state == "rolled_back" and "rolled_back_at" not in item:
        raise ValidationError("rolled_back receipt requires timestamps.rolled_back_at")
    return parsed


def _validate_recovery(value: Any, state: str, project_id: str, managed_before: str) -> tuple[str, dict[str, Any]]:
    if state in COMPLETED_STATES:
        item = _object(value, "receipt.recovery", ["status"])
        if item["status"] != "not_required":
            raise ValidationError("completed receipt must have recovery.status=not_required")
        return state, item
    item = _object(value, "receipt.recovery", ["status", "last_completed_state", "reason"], ["rolled_back_at", "rollback_proof"])
    last = _string(item["last_completed_state"], "receipt.recovery.last_completed_state")
    if last not in COMPLETED_STATES:
        raise ValidationError("receipt.recovery.last_completed_state is invalid")
    _string(item["reason"], "receipt.recovery.reason", 1, 2048)
    if state == "recovery_required":
        if item["status"] != "required" or "rolled_back_at" in item or "rollback_proof" in item:
            raise ValidationError("recovery_required receipt has invalid recovery fields")
    else:
        if item["status"] != "complete" or "rolled_back_at" not in item or "rollback_proof" not in item:
            raise ValidationError("rolled_back receipt requires complete rollback proof")
        rollback = _object(item["rollback_proof"], "receipt.recovery.rollback_proof", ["managed_after_sha256"], ["hub_revision", "hub_paths"])
        rollback_digest = _sha256(rollback["managed_after_sha256"], "receipt.recovery.rollback_proof.managed_after_sha256")
        if rollback_digest != managed_before:
            raise ValidationError("rollback managed_after_sha256 must equal the original managed_before_sha256")
        has_revision = "hub_revision" in rollback
        has_paths = "hub_paths" in rollback
        if last != "prepared" and not (has_revision and has_paths):
            raise ValidationError("rollback from a committed hub state requires hub rollback proof")
        if last == "prepared" and (has_revision or has_paths):
            raise ValidationError("rollback from prepared cannot contain hub rollback proof")
        if has_revision != has_paths:
            raise ValidationError("rollback hub_revision and hub_paths must be supplied together")
        if has_revision:
            _sha40(rollback["hub_revision"], "receipt.recovery.rollback_proof.hub_revision")
            _validate_hub_paths(rollback["hub_paths"], project_id, "receipt.recovery.rollback_proof.hub_paths")
        _datetime(item["rolled_back_at"], "receipt.recovery.rolled_back_at")
    return last, item


def _validate_mirror(value: Any, project_id: str, gateway_state_dir: str) -> None:
    item = _object(value, "receipt.mirror_proof", ["path", "repository_url", "head"])
    path = _absolute_path(item["path"], "receipt.mirror_proof.path")
    expected = f"{gateway_state_dir}/git-mirrors/{project_id}.git"
    if path != expected:
        raise ValidationError("receipt.mirror_proof.path is not the gateway-derived mirror path")
    _repository_url(item["repository_url"], "receipt.mirror_proof.repository_url")
    _sha40(item["head"], "receipt.mirror_proof.head")


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
    if state not in STATES:
        raise ValidationError("receipt.state is invalid")
    project_id = _project_id(value["project_id"], "receipt.project_id")
    repository = _validate_repository_proof(value["repository_proof"], project_id)
    worktree = _object(value["worktree_proof"], "receipt.worktree_proof", ["clean", "status_sha256"])
    _boolean(worktree["clean"], "receipt.worktree_proof.clean")
    _sha256(worktree["status_sha256"], "receipt.worktree_proof.status_sha256")
    _validate_session_proof(value["session_proof"])
    _validate_registry_digests(value["registry_digests"])
    registry_before = value["registry_digests"]["managed_before_sha256"]
    effective_state, recovery = _validate_recovery(value["recovery"], state, project_id, registry_before)
    _validate_created_records(value, project_id, effective_state)
    hub = _object(value["hub"], "receipt.hub", ["before", "paths"], ["after"])
    _sha40(hub["before"], "receipt.hub.before")
    _validate_hub_paths(hub["paths"], project_id, "receipt.hub.paths")
    if effective_state == "prepared":
        if "after" in hub:
            raise ValidationError("prepared proof cannot contain hub.after")
    else:
        if "after" not in hub:
            raise ValidationError(f"{effective_state} proof requires hub.after")
        _sha40(hub["after"], "receipt.hub.after")
    if effective_state == "activated":
        if "mirror_proof" not in value:
            raise ValidationError("activated proof requires mirror_proof")
        _validate_mirror(value["mirror_proof"], project_id, repository["gateway_state_dir"])
    elif "mirror_proof" in value:
        raise ValidationError(f"{effective_state} proof cannot contain mirror_proof")
    parsed_timestamps = _validate_timestamps(value["timestamps"], state, effective_state)
    if state == "rolled_back":
        recovery_time = _parse_datetime(recovery["rolled_back_at"], "receipt.recovery.rolled_back_at")[1]
        if recovery_time != parsed_timestamps["rolled_back_at"]:
            raise ValidationError("recovery.rolled_back_at must equal timestamps.rolled_back_at")
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
