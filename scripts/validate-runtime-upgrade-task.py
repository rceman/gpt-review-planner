#!/usr/bin/env python3
"""Validate the canonical planner runtime-upgrade task declaration."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
TASK_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,80}$")
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
IDENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

TOP_LEVEL = {
    "schema_version", "task_id", "operation", "title", "source_version",
    "target_version", "source_sha", "target_release", "persisted_state_scope",
    "migration_required", "migration", "process_scope", "preflight",
    "activation", "verification", "rollback", "compatibility",
    "success_criterion", "required_gates",
}
COMMAND_KEYS = {"argv", "env", "timeout_seconds", "max_output_bytes"}
MIGRATION_KEYS = {
    "old_schema", "new_schema", "authorized", "authorization_source",
    "direction", "dry_run", "backup", "entry_point",
    "target_decoder_validation", "atomic_commit", "rollback", "removal_condition",
}
COMPATIBILITY_KEYS = {
    "scope", "authorized", "authorization_source", "supported_legacy_versions",
    "direction", "removal_condition",
}
PROCESS_KEYS = {"affected", "unchanged"}
ACTIVATION_KEYS = {"order", "shutdown_required", "affected_processes", "unchanged_processes"}
VERIFICATION_KEYS = {"installed_version", "running_version", "unchanged_processes", "readiness", "protocol", "rollback"}
ROLLBACK_KEYS = {"source", "trigger", "command", "proof"}
NOOP = {"true", "false", "echo", ":", "noop", "no-op"}


class DuplicateKey(ValueError):
    pass


class ContractError(ValueError):
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


def _string(value: Any, label: str, errors: list[str], *, max_bytes: int = 4096) -> bool:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > max_bytes:
        errors.append(f"{label} must be a bounded non-empty string")
        return False
    return True


def _exact_object(value: Any, keys: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    if set(value) != keys:
        errors.append(f"{label} fields must be exactly: {', '.join(sorted(keys))}")
        return False
    return True


def _strings(value: Any, label: str, errors: list[str], *, nonempty: bool = True) -> bool:
    if not isinstance(value, list) or not value or len(value) > 64:
        errors.append(f"{label} must be a non-empty array of at most 64 strings")
        return False
    ok = True
    for index, item in enumerate(value):
        if not isinstance(item, str) or (nonempty and not item.strip()) or len(item.encode("utf-8")) > 4096:
            errors.append(f"{label}[{index}] must be a bounded string")
            ok = False
    return ok


def _command(value: Any, label: str, errors: list[str], *, gate: bool = False) -> bool:
    if not _exact_object(value, COMMAND_KEYS | ({"id"} if gate else set()), label, errors):
        return False
    argv = value.get("argv")
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
        errors.append(f"{label}.argv must be a non-empty string array")
    else:
        first = Path(argv[0]).name.lower()
        joined = " ".join(argv).lower()
        if first in NOOP or (first in {"sh", "bash", "zsh"} and len(argv) >= 3 and argv[1] in {"-c", "-lc"} and argv[2].strip() in NOOP):
            errors.append(f"{label} cannot be a placeholder/no-op command")
        if any(token in joined for token in ("<placeholder>", "todo", "replace_with", "tbd")):
            errors.append(f"{label} contains a placeholder command")
    env = value.get("env")
    if not isinstance(env, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in env.items()):
        errors.append(f"{label}.env must be a string map")
    for key in ("timeout_seconds", "max_output_bytes"):
        number = value.get(key)
        if isinstance(number, bool) or not isinstance(number, int) or number <= 0 or number > (3600 if key == "timeout_seconds" else 64 * 1024 * 1024):
            errors.append(f"{label}.{key} is outside the bounded positive range")
    if gate and (not isinstance(value.get("id"), str) or not re.fullmatch(r"G[1-9][0-9]*", value.get("id", ""))):
        errors.append(f"{label}.id must be a G-number")
    return True


def _semver(value: Any, label: str, errors: list[str]) -> tuple[int, int, int] | None:
    if not isinstance(value, str) or not SEMVER_RE.fullmatch(value):
        errors.append(f"{label} must be strict semantic version")
        return None
    match = SEMVER_RE.fullmatch(value)
    assert match
    return tuple(int(match.group(i)) for i in range(1, 4))


def validate_task(value: Any, *, repo: Path | None = None, authoritative_ref: str = "refs/remotes/origin/main") -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["task root must be an object"]
    unknown = sorted(set(value) - TOP_LEVEL)
    missing = sorted(TOP_LEVEL - set(value))
    errors.extend(f"unknown top-level field: {key}" for key in unknown)
    errors.extend(f"missing top-level field: {key}" for key in missing)
    if unknown or missing:
        return errors
    if value["schema_version"] != 1:
        errors.append("schema_version must be 1")
    if not isinstance(value["task_id"], str) or not TASK_ID_RE.fullmatch(value["task_id"]):
        errors.append("task_id must be a normalized identifier")
    if value["operation"] != "runtime_upgrade":
        errors.append("operation must be runtime_upgrade")
    _string(value["title"], "title", errors, max_bytes=512)
    source_tuple = _semver(value["source_version"], "source_version", errors)
    target_tuple = _semver(value["target_version"], "target_version", errors)
    if source_tuple and target_tuple and target_tuple <= source_tuple:
        errors.append("target_version must be greater than source_version")
    if not isinstance(value["source_sha"], str) or not SHA_RE.fullmatch(value["source_sha"]):
        errors.append("source_sha must be a lowercase 40-character SHA")
    target = value["target_release"]
    if _exact_object(target, {"version", "tag", "sha"}, "target_release", errors):
        if target.get("version") != value["target_version"]:
            errors.append("target_release.version must equal target_version")
        if target.get("tag") != f"v{value['target_version']}":
            errors.append("target_release.tag must equal v<target_version>")
        if not isinstance(target.get("sha"), str) or not SHA_RE.fullmatch(target["sha"]):
            errors.append("target_release.sha must be a lowercase 40-character SHA")
    _strings(value["persisted_state_scope"], "persisted_state_scope", errors)
    if not isinstance(value["migration_required"], bool):
        errors.append("migration_required must be boolean")
    migration = value["migration"]
    if _exact_object(migration, MIGRATION_KEYS, "migration", errors):
        for key in ("old_schema", "new_schema", "authorization_source", "entry_point", "removal_condition"):
            if migration[key] is not None:
                _string(migration[key], f"migration.{key}", errors)
        if not isinstance(migration["authorized"], bool):
            errors.append("migration.authorized must be boolean")
        if migration["direction"] not in {"none", "forward"}:
            errors.append("migration.direction must be none or forward")
        for key in ("dry_run", "backup", "target_decoder_validation", "atomic_commit", "rollback"):
            if not isinstance(migration[key], bool):
                errors.append(f"migration.{key} must be boolean")
        if not value["migration_required"] and (
            migration["old_schema"] is not None or migration["new_schema"] is not None
        ):
            errors.append("schema-changing migration cannot be declared without migration_required")
        if value["migration_required"]:
            if not migration["authorized"] or not migration["authorization_source"] or migration["direction"] != "forward":
                errors.append("required migration needs explicit authorization and forward direction")
            if migration["old_schema"] == migration["new_schema"]:
                errors.append("required migration must change schema")
            if not all(migration[key] for key in ("dry_run", "backup", "target_decoder_validation", "atomic_commit", "rollback")):
                errors.append("required migration must declare dry-run, backup, decoder, atomic commit, and rollback")
    process = value["process_scope"]
    if _exact_object(process, PROCESS_KEYS, "process_scope", errors):
        _strings(process["affected"], "process_scope.affected", errors)
        _strings(process["unchanged"], "process_scope.unchanged", errors)
        if isinstance(process.get("affected"), list) and len(process["affected"]) != len(set(process["affected"])):
            errors.append("process_scope.affected must not contain duplicates")
        if isinstance(process.get("unchanged"), list) and len(process["unchanged"]) != len(set(process["unchanged"])):
            errors.append("process_scope.unchanged must not contain duplicates")
        if isinstance(process.get("affected"), list) and isinstance(process.get("unchanged"), list) and set(process["affected"]) & set(process["unchanged"]):
            errors.append("affected and unchanged process sets must be disjoint")
    preflight = value["preflight"]
    preflight_keys = {"installed_version_check", "running_version_check", "persisted_state_check", "target_decoder_validation", "readiness_check", "protocol_check"}
    if _exact_object(preflight, preflight_keys, "preflight", errors):
        for key in sorted(preflight_keys):
            _command(preflight[key], f"preflight.{key}", errors)
    activation = value["activation"]
    if _exact_object(activation, ACTIVATION_KEYS, "activation", errors):
        if not isinstance(activation["order"], list) or any(not isinstance(item, str) for item in activation["order"]):
            errors.append("activation.order must be a string array")
        else:
            order = activation["order"]
            required_order = {"inspect", "prepare", "backup", "migrate", "target_decoder_validation", "activate", "verify"}
            if set(order) != required_order or len(order) != len(required_order):
                errors.append("activation.order must contain each declared upgrade phase exactly once")
            if "target_decoder_validation" in order and "activate" in order and order.index("target_decoder_validation") > order.index("activate"):
                errors.append("target decoder validation must precede activation")
        if not isinstance(activation["shutdown_required"], bool):
            errors.append("activation.shutdown_required must be boolean")
        _strings(activation["affected_processes"], "activation.affected_processes", errors)
        _strings(activation["unchanged_processes"], "activation.unchanged_processes", errors)
        if isinstance(process, dict) and isinstance(activation.get("affected_processes"), list) and isinstance(process.get("affected"), list) and set(activation["affected_processes"]) != set(process["affected"]):
            errors.append("activation.affected_processes must equal process_scope.affected")
        if isinstance(process, dict) and isinstance(activation.get("unchanged_processes"), list) and isinstance(process.get("unchanged"), list) and set(activation["unchanged_processes"]) != set(process["unchanged"]):
            errors.append("activation.unchanged_processes must equal process_scope.unchanged")
    verification = value["verification"]
    if _exact_object(verification, VERIFICATION_KEYS, "verification", errors):
        for key in VERIFICATION_KEYS:
            _strings(verification[key], f"verification.{key}", errors)
        proof_values = verification.get("unchanged_processes")
        proof_text = " ".join(proof_values).lower() if isinstance(proof_values, list) and all(isinstance(item, str) for item in proof_values) else ""
        if isinstance(process, dict) and isinstance(process.get("unchanged"), list):
            for process_name in process["unchanged"]:
                if process_name.lower() not in proof_text:
                    errors.append(
                        f"verification.unchanged_processes must prove unchanged process: {process_name}"
                    )
    rollback = value["rollback"]
    if _exact_object(rollback, ROLLBACK_KEYS, "rollback", errors):
        for key in ROLLBACK_KEYS:
            if key == "proof":
                _strings(rollback[key], "rollback.proof", errors)
            else:
                _string(rollback[key], f"rollback.{key}", errors)
    compatibility = value["compatibility"]
    if _exact_object(compatibility, COMPATIBILITY_KEYS, "compatibility", errors):
        scope = compatibility["scope"]
        versions = compatibility["supported_legacy_versions"]
        if scope == "none":
            expected = {"authorized": False, "authorization_source": None, "supported_legacy_versions": [], "direction": "none", "removal_condition": None}
            if any(compatibility[key] != val for key, val in expected.items()):
                errors.append("unauthorized compatibility scope=none must contain no legacy declaration")
        elif scope == "explicit":
            if compatibility["authorized"] is not True or not compatibility["authorization_source"] or not isinstance(versions, list) or not versions or compatibility["direction"] == "none" or not compatibility["removal_condition"]:
                errors.append("explicit compatibility requires authorization source, supported versions, direction, and removal condition")
        else:
            errors.append("compatibility.scope must be none or explicit")
        if not isinstance(compatibility["authorized"], bool):
            errors.append("compatibility.authorized must be boolean")
        if not isinstance(versions, list) or len(versions) > 64 or any(not isinstance(item, str) or not item.strip() or len(item.encode("utf-8")) > 256 for item in versions):
            errors.append("compatibility.supported_legacy_versions must be a string array")
        if compatibility["direction"] not in {"none", "forward", "bidirectional"}:
            errors.append("compatibility.direction is invalid")
        for key in ("authorization_source", "removal_condition"):
            if compatibility[key] is not None and not isinstance(compatibility[key], str):
                errors.append(f"compatibility.{key} must be string or null")
        compatibility_text = (versions if isinstance(versions, list) else []) + [compatibility.get("removal_condition") or ""]
        if any(isinstance(item, str) and any(term in item.lower() for term in ("fallback", "dual reader", "permanent alias")) for item in compatibility_text):
            errors.append("permanent fallback compatibility is forbidden")
        if value["migration_required"] and not compatibility["authorized"]:
            errors.append("schema-changing migration requires explicit compatibility authorization")
    _string(value["success_criterion"], "success_criterion", errors)
    gates = value["required_gates"]
    if not isinstance(gates, list) or not gates or len(gates) > 128:
        errors.append("required_gates must be a non-empty array of at most 128 gates")
    else:
        ids: list[str] = []
        for index, gate in enumerate(gates):
            _command(gate, f"required_gates[{index}]", errors, gate=True)
            gate_id = gate.get("id") if isinstance(gate, dict) else None
            if gate_id in ids:
                errors.append(f"duplicate gate id: {gate_id}")
            if isinstance(gate_id, str):
                ids.append(gate_id)
        if ids != [f"G{i}" for i in range(1, len(ids) + 1)]:
            errors.append("required_gates must use ordered G1..Gn identifiers")
    if repo is not None and not errors:
        try:
            version = (repo / "VERSION").read_text(encoding="utf-8").strip()
            if version != value["source_version"]:
                errors.append("source_version does not match repository VERSION")
            actual = subprocess.run(["git", "-C", str(repo), "rev-parse", authoritative_ref], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            if actual.returncode != 0 or actual.stdout.strip() != value["source_sha"]:
                errors.append("source_sha does not match the authoritative repository ref")
            status = subprocess.run(
                ["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if status.returncode != 0 or status.stdout:
                errors.append("planner repository worktree must be clean")
        except (OSError, UnicodeError):
            errors.append("repository identity could not be verified")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", type=Path)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--authoritative-ref", default="refs/remotes/origin/main")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    errors: list[str]
    try:
        value = load_json(args.task)
        errors = validate_task(value, repo=args.repo, authoritative_ref=args.authoritative_ref)
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKey) as exc:
        errors = [f"invalid runtime-upgrade task JSON: {exc}"]
    if args.format == "json":
        print(json.dumps({"schema_version": 1, "valid": not errors, "errors": errors}, sort_keys=True, separators=(",", ":")))
    elif errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
    else:
        print(f"PASS: {args.task}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
