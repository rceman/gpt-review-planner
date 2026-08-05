#!/usr/bin/env python3
"""Validate the planner-side Airelay managed-upgrade contract.

This module is deliberately a strict, dependency-free validator. The planner
describes identities, authorizations, and proofs; it does not install, stop,
start, signal, or otherwise control an Airelay process.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable


class ValidationError(ValueError):
    """Raised when a recipe, request, or receipt violates the contract."""


ROOT = Path(__file__).resolve().parents[1]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
ENV_RE = re.compile(r"^[A-Z_][A-Z0-9_]{0,127}$")
FLAG_RE = re.compile(r"^--[A-Za-z0-9][A-Za-z0-9-]{0,63}$")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
SHELL_CHARS = set(";|&$" + chr(96) + "()<>" )
MAX_SAFE_INTEGER = 9007199254740991
RESOLUTION_KINDS = {"direct", "symlink", "wrapper"}


def _duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: str | Path) -> Any:
    """Load UTF-8 JSON while rejecting duplicate object keys."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc
    try:
        return json.loads(text, object_pairs_hook=_duplicate_pairs)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValidationError(f"invalid JSON in {path}: {exc}") from exc


def _fail(path: str, message: str) -> None:
    raise ValidationError(f"{path}: {message}")


def _object(value: Any, path: str, keys: Iterable[str], required: Iterable[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "must be an object")
    allowed = set(keys)
    required_set = set(required)
    unknown = sorted(set(value) - allowed)
    missing = sorted(required_set - set(value))
    if unknown:
        _fail(path, f"unknown field(s): {', '.join(unknown)}")
    if missing:
        _fail(path, f"missing field(s): {', '.join(missing)}")
    return value


def _string(value: Any, path: str, *, nonempty: bool = True, max_length: int = 4096) -> str:
    if not isinstance(value, str):
        _fail(path, "must be a string")
    if nonempty and not value:
        _fail(path, "must not be empty")
    if len(value) > max_length:
        _fail(path, f"must be at most {max_length} characters")
    if CONTROL_RE.search(value):
        _fail(path, "contains a control character")
    return value


def _match(value: Any, path: str, regex: re.Pattern[str]) -> str:
    value = _string(value, path)
    if not regex.fullmatch(value):
        _fail(path, "has an invalid format")
    return value


def _sha(value: Any, path: str) -> str:
    return _match(value, path, SHA256_RE)


def _semver(value: Any, path: str) -> str:
    return _match(value, path, SEMVER_RE)


def _identifier(value: Any, path: str) -> str:
    return _match(value, path, IDENTIFIER_RE)


def _session_key(value: Any, path: str) -> str:
    return _match(value, path, SESSION_RE)


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    # JSON Schema integer includes integral JSON numbers such as 1.0, but
    # never booleans, fractional values, infinities, or unsafe integers.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(path, "must be a JSON integer")
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        _fail(path, "must be an integral finite number")
    converted = int(value)
    if converted < minimum or converted > MAX_SAFE_INTEGER:
        _fail(path, f"must be in [{minimum}, {MAX_SAFE_INTEGER}]")
    return converted


def _positive_integer(value: Any, path: str) -> int:
    return _integer(value, path, minimum=1)


def _nonnegative_integer(value: Any, path: str) -> int:
    return _integer(value, path, minimum=0)


def _absolute_path(value: Any, path: str) -> str:
    value = _string(value, path, max_length=4096)
    if not value.startswith("/") or value == "/":
        _fail(path, "must be a non-root absolute path")
    if "\\" in value or "//" in value:
        _fail(path, "must use normalized POSIX components")
    components = value.split("/")[1:]
    if any(not component or component in {".", ".."} for component in components):
        _fail(path, "must not contain empty, dot, or traversal components")
    return value


def _resolution_kind(value: Any, path: str, invocation_path: str, resolved_path: str) -> str:
    if not isinstance(value, str) or value not in RESOLUTION_KINDS:
        _fail(path, "must be direct, symlink, or wrapper")
    if value == "direct" and invocation_path != resolved_path:
        _fail(path, "direct requires equal invocation_path and resolved_path")
    if value in {"symlink", "wrapper"} and invocation_path == resolved_path:
        _fail(path, f"{value} requires different invocation_path and resolved_path")
    return value


def _safe_token(value: Any, path: str) -> str:
    value = _string(value, path, max_length=1024)
    if any(char.isspace() or char in SHELL_CHARS for char in value):
        _fail(path, "must be a shell-free token")
    if '"' in value or "'" in value or "\\" in value:
        _fail(path, "must not contain quoting or escaping")
    lowered = value.lower()
    if any(marker in lowered for marker in ("token=", "password=", "secret=", "api_key=", "apikey=")):
        _fail(path, "must not contain secret material")
    return value


def _validate_argv(value: Any, path: str) -> list[str]:
    argv = _array(value, path, min_items=1)
    for index, token in enumerate(argv):
        _safe_token(token, f"{path}[{index}]")
    return argv


def _validate_argv_binding(argv: list[str], resume_identity: str, flags: list[str], path: str) -> None:
    resume_positions = [index for index, token in enumerate(argv) if token == "resume"]
    if len(resume_positions) != 1:
        _fail(path, "must contain exactly one resume token")
    resume_index = resume_positions[0]
    if resume_index + 1 >= len(argv) or argv[resume_index + 1] != resume_identity:
        _fail(path, "resume identity must immediately follow the resume token")
    for index, flag in enumerate(flags):
        if flag not in argv:
            _fail(f"{path}.approved_flags[{index}]", "must occur in argv")
    for index, token in enumerate(argv):
        if token.startswith("--") and token not in flags:
            _fail(f"{path}[{index}]", "flag is not listed in approved_flags")


def _validate_flags(value: Any, path: str, argv: list[str]) -> list[str]:
    flags = _array(value, path, max_items=64)
    for index, flag in enumerate(flags):
        _match(flag, f"{path}[{index}]", FLAG_RE)
    return flags


def _array(value: Any, path: str, *, min_items: int = 0, max_items: int = 128) -> list[Any]:
    if not isinstance(value, list):
        _fail(path, "must be an array")
    if len(value) < min_items or len(value) > max_items:
        _fail(path, f"must contain between {min_items} and {max_items} items")
    try:
        serialised = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
    except TypeError:
        _fail(path, "contains an unsupported item")
    if len(set(serialised)) != len(serialised):
        _fail(path, "must not contain duplicates")
    return value


def _datetime(value: Any, path: str) -> _dt.datetime:
    value = _string(value, path, max_length=64)
    if not value.endswith("Z") and not re.search(r"[+-][0-9]{2}:[0-9]{2}$", value):
        _fail(path, "must be RFC3339 with an explicit timezone")
    try:
        parsed = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        _fail(path, f"invalid RFC3339 timestamp: {exc}")
    if parsed.tzinfo is None:
        _fail(path, "must include a timezone")
    return parsed.astimezone(_dt.timezone.utc)


def _ordered_times(values: list[tuple[str, _datetime.datetime]], path: str) -> None:
    for (left_name, left), (right_name, right) in zip(values, values[1:]):
        if right < left:
            _fail(path, f"{right_name} must not precede {left_name}")


def _recipe_digest(document: dict[str, Any]) -> str:
    payload = dict(document)
    payload.pop("recipe_sha256", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_target_release(value: Any, path: str = "target_release") -> dict[str, Any]:
    target = _object(value, path, {"version", "release_path", "build_sha256"}, {"version", "release_path", "build_sha256"})
    version = _semver(target["version"], f"{path}.version")
    release_path = _absolute_path(target["release_path"], f"{path}.release_path")
    if release_path.rstrip("/").rsplit("/", 1)[-1] != version:
        _fail(f"{path}.release_path", "must end with the target version")
    _sha(target["build_sha256"], f"{path}.build_sha256")
    return target


def _validate_authorization(value: Any, path: str) -> dict[str, Any]:
    authorization = _object(value, path, {"authorized", "source"}, {"authorized"})
    if not isinstance(authorization["authorized"], bool):
        _fail(f"{path}.authorized", "must be boolean")
    source = authorization.get("source")
    if authorization["authorized"]:
        _string(source, f"{path}.source", max_length=1024)
    elif source is not None:
        _fail(f"{path}.source", "must be null or absent when authorization is false")
    return authorization


def validate_recipe(document: Any) -> dict[str, Any]:
    recipe = _object(
        document,
        "recipe",
        {"schema_version", "recipe_sha256", "session_key", "profile", "working_directory", "executable", "child", "resume", "approved_flags", "environment_references"},
        {"schema_version", "recipe_sha256", "session_key", "profile", "working_directory", "executable", "child", "resume", "approved_flags", "environment_references"},
    )
    if recipe["schema_version"] != 1:
        _fail("recipe.schema_version", "must be 1")
    supplied_digest = _sha(recipe["recipe_sha256"], "recipe.recipe_sha256")
    session_key = _session_key(recipe["session_key"], "recipe.session_key")
    _identifier(recipe["profile"], "recipe.profile")
    _absolute_path(recipe["working_directory"], "recipe.working_directory")
    executable = _object(recipe["executable"], "recipe.executable", {"invocation_path", "resolved_path", "resolution_kind", "version", "controller_protocol_version"}, {"invocation_path", "resolved_path", "resolution_kind", "version", "controller_protocol_version"})
    executable_invocation = _absolute_path(executable["invocation_path"], "recipe.executable.invocation_path")
    executable_resolved = _absolute_path(executable["resolved_path"], "recipe.executable.resolved_path")
    _resolution_kind(recipe["executable"]["resolution_kind"], "recipe.executable.resolution_kind", executable_invocation, executable_resolved)
    _semver(executable["version"], "recipe.executable.version")
    _positive_integer(executable["controller_protocol_version"], "recipe.executable.controller_protocol_version")
    child = _object(recipe["child"], "recipe.child", {"invocation_path", "resolved_path", "resolution_kind", "argv"}, {"invocation_path", "resolved_path", "resolution_kind", "argv"})
    child_invocation = _absolute_path(child["invocation_path"], "recipe.child.invocation_path")
    child_resolved = _absolute_path(child["resolved_path"], "recipe.child.resolved_path")
    _resolution_kind(child["resolution_kind"], "recipe.child.resolution_kind", child_invocation, child_resolved)
    argv = _validate_argv(child["argv"], "recipe.child.argv")
    resume = _object(recipe["resume"], "recipe.resume", {"identity"}, {"identity"})
    resume_identity = _match(resume["identity"], "recipe.resume.identity", UUID_RE)
    if resume_identity == session_key:
        _fail("recipe.resume.identity", "must be a Codex resume UUID, not session_key")
    flags = _validate_flags(recipe["approved_flags"], "recipe.approved_flags", argv)
    _validate_argv_binding(argv, resume_identity, flags, "recipe.child.argv")
    environment = _array(recipe["environment_references"], "recipe.environment_references", max_items=64)
    for index, reference in enumerate(environment):
        _match(reference, f"recipe.environment_references[{index}]", ENV_RE)
    if _recipe_digest(recipe) != supplied_digest:
        _fail("recipe.recipe_sha256", "does not match the canonical recipe digest")
    return recipe


def _validate_selected_session(value: Any, index: int) -> dict[str, Any]:
    path = f"request.selected_sessions[{index}]"
    keys = {
        "session_key",
        "expected_profile",
        "expected_version",
        "expected_recipe_sha256",
        "expected_pid",
        "expected_controller_protocol_version",
        "expected_working_directory",
        "expected_executable_invocation_path",
        "expected_executable_resolved_path",
        "expected_executable_resolution_kind",
        "expected_child_invocation_path",
        "expected_child_resolved_path",
        "expected_child_resolution_kind",
        "expected_child_argv",
        "expected_approved_flags",
        "expected_resume_identity",
    }
    session = _object(value, path, keys, keys)
    key = _session_key(session["session_key"], f"{path}.session_key")
    _identifier(session["expected_profile"], f"{path}.expected_profile")
    _semver(session["expected_version"], f"{path}.expected_version")
    _sha(session["expected_recipe_sha256"], f"{path}.expected_recipe_sha256")
    _positive_integer(session["expected_pid"], f"{path}.expected_pid")
    _positive_integer(session["expected_controller_protocol_version"], f"{path}.expected_controller_protocol_version")
    _absolute_path(session["expected_working_directory"], f"{path}.expected_working_directory")
    executable_invocation = _absolute_path(session["expected_executable_invocation_path"], f"{path}.expected_executable_invocation_path")
    executable_resolved = _absolute_path(session["expected_executable_resolved_path"], f"{path}.expected_executable_resolved_path")
    _resolution_kind(session["expected_executable_resolution_kind"], f"{path}.expected_executable_resolution_kind", executable_invocation, executable_resolved)
    child_invocation = _absolute_path(session["expected_child_invocation_path"], f"{path}.expected_child_invocation_path")
    child_resolved = _absolute_path(session["expected_child_resolved_path"], f"{path}.expected_child_resolved_path")
    _resolution_kind(session["expected_child_resolution_kind"], f"{path}.expected_child_resolution_kind", child_invocation, child_resolved)
    argv = _validate_argv(session["expected_child_argv"], f"{path}.expected_child_argv")
    flags = _validate_flags(session["expected_approved_flags"], f"{path}.expected_approved_flags", argv)
    resume_identity = _match(session["expected_resume_identity"], f"{path}.expected_resume_identity", UUID_RE)
    if resume_identity == key:
        _fail(f"{path}.expected_resume_identity", "must be a Codex resume UUID, not session_key")
    _validate_argv_binding(argv, resume_identity, flags, f"{path}.expected_child_argv")
    return session


def validate_request(document: Any) -> dict[str, Any]:
    request = _object(document, "request", {"schema_version", "operation_id", "target_release", "selected_sessions", "graceful_timeout_seconds", "force_stop_policy", "authorizations"}, {"schema_version", "operation_id", "target_release", "selected_sessions", "graceful_timeout_seconds", "force_stop_policy", "authorizations"})
    if request["schema_version"] != 1:
        _fail("request.schema_version", "must be 1")
    _match(request["operation_id"], "request.operation_id", UUID_RE)
    _validate_target_release(request["target_release"])
    selected = _array(request["selected_sessions"], "request.selected_sessions", min_items=1, max_items=64)
    sessions = [_validate_selected_session(item, index) for index, item in enumerate(selected)]
    keys = [item["session_key"] for item in sessions]
    if len(set(keys)) != len(keys):
        _fail("request.selected_sessions", "session_key values must be unique")
    if "airelay_master" in keys and keys[-1] != "airelay_master":
        _fail("request.selected_sessions", "airelay_master must be last when selected")
    _positive_integer(request["graceful_timeout_seconds"], "request.graceful_timeout_seconds")
    force_policy = _object(request["force_stop_policy"], "request.force_stop_policy", {"mode"}, {"mode"})
    if force_policy["mode"] not in {"never", "owner_authorized"}:
        _fail("request.force_stop_policy.mode", "must be never or owner_authorized")
    auths = _object(request["authorizations"], "request.authorizations", {"install", "restart", "force_stop"}, {"install", "restart", "force_stop"})
    parsed_auths = {key: _validate_authorization(auths[key], f"request.authorizations.{key}") for key in ("install", "restart", "force_stop")}
    for key in ("install", "restart"):
        if not parsed_auths[key]["authorized"]:
            _fail(f"request.authorizations.{key}", "must be authorized for an upgrade request")
    if force_policy["mode"] == "never" and parsed_auths["force_stop"]["authorized"]:
        _fail("request.authorizations.force_stop", "must be unauthorized when force_stop_policy is never")
    if force_policy["mode"] == "owner_authorized" and not parsed_auths["force_stop"]["authorized"]:
        _fail("request.authorizations.force_stop", "must be authorized when force_stop_policy is owner_authorized")
    return request


IDENTITY_KEYS = {
    "recipe_sha256",
    "profile",
    "version",
    "pid",
    "controller_protocol_version",
    "working_directory",
    "executable_invocation_path",
    "executable_resolved_path",
    "executable_resolution_kind",
    "child_invocation_path",
    "child_resolved_path",
    "child_resolution_kind",
    "child_argv",
    "approved_flags",
    "resume_identity",
}


def _validate_identity(value: Any, path: str, session_key: str) -> dict[str, Any]:
    identity = _object(value, path, IDENTITY_KEYS, IDENTITY_KEYS)
    _sha(identity["recipe_sha256"], f"{path}.recipe_sha256")
    _identifier(identity["profile"], f"{path}.profile")
    _semver(identity["version"], f"{path}.version")
    _positive_integer(identity["pid"], f"{path}.pid")
    _positive_integer(identity["controller_protocol_version"], f"{path}.controller_protocol_version")
    _absolute_path(identity["working_directory"], f"{path}.working_directory")
    executable_invocation = _absolute_path(identity["executable_invocation_path"], f"{path}.executable_invocation_path")
    executable_resolved = _absolute_path(identity["executable_resolved_path"], f"{path}.executable_resolved_path")
    _resolution_kind(identity["executable_resolution_kind"], f"{path}.executable_resolution_kind", executable_invocation, executable_resolved)
    child_invocation = _absolute_path(identity["child_invocation_path"], f"{path}.child_invocation_path")
    child_resolved = _absolute_path(identity["child_resolved_path"], f"{path}.child_resolved_path")
    _resolution_kind(identity["child_resolution_kind"], f"{path}.child_resolution_kind", child_invocation, child_resolved)
    argv = _validate_argv(identity["child_argv"], f"{path}.child_argv")
    flags = _validate_flags(identity["approved_flags"], f"{path}.approved_flags", argv)
    resume_identity = _match(identity["resume_identity"], f"{path}.resume_identity", UUID_RE)
    if resume_identity == session_key:
        _fail(f"{path}.resume_identity", "must be a Codex resume UUID, not session_key")
    _validate_argv_binding(argv, resume_identity, flags, f"{path}.child_argv")
    return identity


def _validate_failure(value: Any, path: str) -> dict[str, Any]:
    failure = _object(value, path, {"code", "message", "at"}, {"code", "message", "at"})
    _identifier(failure["code"], f"{path}.code")
    _string(failure["message"], f"{path}.message", max_length=2048)
    _datetime(failure["at"], f"{path}.at")
    return failure


def _validate_session_timestamps(value: Any, path: str) -> dict[str, Any]:
    allowed = {"started_at", "drained_at", "stopped_at", "starting_at", "ready_at", "rollback_started_at", "rolled_back_at", "updated_at"}
    timestamps = _object(value, path, allowed, {"started_at", "updated_at"})
    names = ["started_at", "drained_at", "stopped_at", "starting_at", "ready_at", "rollback_started_at", "rolled_back_at", "updated_at"]
    parsed = [(name, _datetime(timestamps[name], f"{path}.{name}")) for name in names if name in timestamps]
    _ordered_times(parsed, path)
    return timestamps


def _validate_readiness(value: Any, path: str, identity: dict[str, Any]) -> dict[str, Any]:
    readiness = _object(value, path, {"status", "checked_at", "identity"}, {"status", "checked_at", "identity"})
    if readiness["status"] != "ready":
        _fail(f"{path}.status", "must be ready for a completed managed upgrade proof")
    _datetime(readiness["checked_at"], f"{path}.checked_at")
    if readiness["identity"] != identity:
        _fail(f"{path}.identity", "must exactly equal new_identity")
    return readiness


def _validate_rollback_proof(value: Any, path: str, old_identity: dict[str, Any]) -> dict[str, Any]:
    proof = _object(value, path, {"old_identity", "restored_at"}, {"old_identity", "restored_at"})
    if proof["old_identity"] != old_identity:
        _fail(f"{path}.old_identity", "must exactly equal the original identity")
    _datetime(proof["restored_at"], f"{path}.restored_at")
    return proof


def _validate_session_receipt(value: Any, index: int, target_version: str) -> dict[str, Any]:
    path = f"receipt.sessions[{index}]"
    allowed = {"session_key", "state", "old_identity", "new_identity", "readiness", "timestamps", "failure", "rollback_proof"}
    session = _object(value, path, allowed, {"session_key", "state", "old_identity", "timestamps"})
    key = _session_key(session["session_key"], f"{path}.session_key")
    state = session["state"]
    states = {"pending", "drained", "stopped", "starting", "ready", "rollback_starting", "rolled_back", "failed"}
    if state not in states:
        _fail(f"{path}.state", "unsupported session state")
    old = _validate_identity(session["old_identity"], f"{path}.old_identity", key)
    _validate_session_timestamps(session["timestamps"], f"{path}.timestamps")
    new = None
    if "new_identity" in session:
        new = _validate_identity(session["new_identity"], f"{path}.new_identity", key)
        if new["version"] != target_version:
            _fail(f"{path}.new_identity.version", "must equal target_release.version")
        if new == old:
            _fail(f"{path}.new_identity", "must prove a changed runtime identity")
    if state in {"starting", "ready", "rollback_starting"} and new is None:
        _fail(path, f"{state} requires new_identity")
    if state == "ready":
        if "readiness" not in session:
            _fail(path, "ready requires readiness proof")
        _validate_readiness(session["readiness"], f"{path}.readiness", new)  # type: ignore[arg-type]
        if "ready_at" not in session["timestamps"]:
            _fail(path, "ready requires ready_at")
    elif "readiness" in session:
        _fail(path, "readiness is only valid for ready sessions")
    if state == "failed":
        if "failure" not in session:
            _fail(path, "failed requires failure")
        _validate_failure(session["failure"], f"{path}.failure")
    elif "failure" in session:
        _fail(path, "failure is only valid for failed sessions")
    if state == "rolled_back":
        if "rollback_proof" not in session:
            _fail(path, "rolled_back requires rollback_proof")
        _validate_rollback_proof(session["rollback_proof"], f"{path}.rollback_proof", old)
        if "rolled_back_at" not in session["timestamps"]:
            _fail(path, "rolled_back requires rolled_back_at")
    elif "rollback_proof" in session:
        _fail(path, "rollback_proof is only valid for rolled_back sessions")
    return session


def _validate_top_timestamps(value: Any, path: str, state: str) -> dict[str, Any]:
    allowed = {"started_at", "prepared_at", "completed_at", "rollback_started_at", "rolled_back_at", "updated_at"}
    timestamps = _object(value, path, allowed, {"started_at", "updated_at"})
    if state == "succeeded" and not {"prepared_at", "completed_at"}.issubset(timestamps):
        _fail(path, "succeeded requires prepared_at and completed_at")
    if state == "rolled_back" and not {"rollback_started_at", "rolled_back_at"}.issubset(timestamps):
        _fail(path, "rolled_back requires rollback_started_at and rolled_back_at")
    names = ["started_at", "prepared_at", "completed_at", "rollback_started_at", "rolled_back_at", "updated_at"]
    parsed = [(name, _datetime(timestamps[name], f"{path}.{name}")) for name in names if name in timestamps]
    _ordered_times(parsed, path)
    return timestamps


def _validate_prompt_window(value: Any) -> dict[str, Any]:
    window = _object(value, "receipt.prompt_rejection_window", {"started_at", "ended_at", "rejected_count"}, {"started_at", "ended_at", "rejected_count"})
    started = _datetime(window["started_at"], "receipt.prompt_rejection_window.started_at")
    ended = _datetime(window["ended_at"], "receipt.prompt_rejection_window.ended_at")
    if ended < started:
        _fail("receipt.prompt_rejection_window", "ended_at must not precede started_at")
    _nonnegative_integer(window["rejected_count"], "receipt.prompt_rejection_window.rejected_count")
    return window


def _validate_rollback(value: Any, path: str) -> dict[str, Any]:
    rollback = _object(value, path, {"reason", "started_at", "completed_at"}, {"reason", "started_at"})
    _string(rollback["reason"], f"{path}.reason", max_length=2048)
    started = _datetime(rollback["started_at"], f"{path}.started_at")
    if "completed_at" in rollback and _datetime(rollback["completed_at"], f"{path}.completed_at") < started:
        _fail(path, "completed_at must not precede started_at")
    return rollback


def validate_receipt(document: Any) -> dict[str, Any]:
    allowed = {"schema_version", "operation_id", "request_sha256", "state", "target_release", "sessions", "prompt_rejection_window", "timestamps", "failure", "rollback"}
    receipt = _object(document, "receipt", allowed, {"schema_version", "operation_id", "request_sha256", "state", "target_release", "sessions", "prompt_rejection_window", "timestamps"})
    if receipt["schema_version"] != 1:
        _fail("receipt.schema_version", "must be 1")
    _match(receipt["operation_id"], "receipt.operation_id", UUID_RE)
    _sha(receipt["request_sha256"], "receipt.request_sha256")
    state = receipt["state"]
    states = {"prepared", "running", "succeeded", "rollback_required", "rolled_back", "failed"}
    if state not in states:
        _fail("receipt.state", "unsupported aggregate state")
    target = _validate_target_release(receipt["target_release"])
    sessions = _array(receipt["sessions"], "receipt.sessions", min_items=1, max_items=64)
    parsed_sessions = [_validate_session_receipt(item, index, target["version"]) for index, item in enumerate(sessions)]
    keys = [item["session_key"] for item in parsed_sessions]
    if len(set(keys)) != len(keys):
        _fail("receipt.sessions", "session_key values must be unique")
    if "airelay_master" in keys and keys[-1] != "airelay_master":
        _fail("receipt.sessions", "airelay_master must be last when selected")
    _validate_prompt_window(receipt["prompt_rejection_window"])
    _validate_top_timestamps(receipt["timestamps"], "receipt.timestamps", state)
    if state == "succeeded":
        if any(item["state"] != "ready" for item in parsed_sessions):
            _fail("receipt.sessions", "succeeded requires every session to be ready")
        if "failure" in receipt or "rollback" in receipt:
            _fail("receipt", "succeeded must not contain failure or rollback")
    elif state == "failed":
        if "failure" not in receipt:
            _fail("receipt", "failed requires aggregate failure")
        _validate_failure(receipt["failure"], "receipt.failure")
        if "rollback" in receipt:
            _fail("receipt", "failed must not contain rollback")
        if not any(item["state"] == "failed" for item in parsed_sessions):
            _fail("receipt.sessions", "failed requires a failed session")
    elif "failure" in receipt:
        _fail("receipt.failure", "aggregate failure is only valid for failed")
    if state in {"rollback_required", "rolled_back"}:
        if "rollback" not in receipt:
            _fail("receipt", f"{state} requires aggregate rollback")
        _validate_rollback(receipt["rollback"], "receipt.rollback")
        if state == "rollback_required" and not any(item["state"] in {"failed", "rollback_starting"} for item in parsed_sessions):
            _fail("receipt.sessions", "rollback_required requires a failed or rollback_starting session")
        if state == "rolled_back" and any(item["state"] != "rolled_back" for item in parsed_sessions):
            _fail("receipt.sessions", "rolled_back requires every session to be rolled_back")
    elif "rollback" in receipt:
        _fail("receipt.rollback", "aggregate rollback is only valid for rollback states")
    if state == "prepared" and any(item["state"] != "pending" for item in parsed_sessions):
        _fail("receipt.sessions", "prepared requires pending sessions")
    return receipt


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--recipe", type=Path)
    group.add_argument("--request", type=Path)
    group.add_argument("--receipt", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    kind = "document"
    try:
        document = load_json(args.recipe or args.request or args.receipt)
        if args.recipe:
            validate_recipe(document)
            kind = "recipe"
        elif args.request:
            validate_request(document)
            kind = "request"
        else:
            validate_receipt(document)
            kind = "receipt"
    except ValidationError as exc:
        print(f"invalid {kind}: {exc}", file=sys.stderr)
        return 2
    path = args.recipe or args.request or args.receipt
    print(f"valid {kind}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
