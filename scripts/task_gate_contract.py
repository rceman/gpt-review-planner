#!/usr/bin/env python3
"""Strict task-to-gate contract primitives and deterministic generation."""
from __future__ import annotations

import hashlib
import json
import re
import shlex
import tempfile
from pathlib import Path

CONTRACT_FIELDS = {
    "schema_version", "project_id", "task_id", "task_sha256", "required_gates"
}
GATE_FIELDS = {
    "id", "name", "command", "argv", "env", "cwd", "parser",
    "metric", "timeout_seconds", "max_output_bytes"
}
PARSERS = {"exit", "unittest", "pytest"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class TaskGateContractError(ValueError):
    pass


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise TaskGateContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError, TaskGateContractError) as exc:
        raise TaskGateContractError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise TaskGateContractError("JSON value must be an object")
    return value


def _canonical_cwd(value: object) -> str:
    if not isinstance(value, str):
        raise TaskGateContractError("cwd must be a string")
    if value == "":
        return value
    path = Path(value)
    if path.is_absolute() or "\\" in value or any(part in {"", ".", ".."} for part in path.parts):
        raise TaskGateContractError("cwd must be a canonical repository-relative path")
    return value


def validate_contract(value: dict) -> dict:
    if set(value) != CONTRACT_FIELDS:
        raise TaskGateContractError("task gate contract fields invalid")
    if value["schema_version"] != 1:
        raise TaskGateContractError("unsupported task gate contract schema version")
    if not isinstance(value["project_id"], str) or not ID_RE.fullmatch(value["project_id"]):
        raise TaskGateContractError("invalid project_id")
    if not isinstance(value["task_id"], str) or not UUID_RE.fullmatch(value["task_id"]):
        raise TaskGateContractError("invalid lowercase task_id")
    if not isinstance(value["task_sha256"], str) or not SHA256_RE.fullmatch(value["task_sha256"]):
        raise TaskGateContractError("invalid task_sha256")
    gates = value["required_gates"]
    if not isinstance(gates, list) or not gates:
        raise TaskGateContractError("required_gates must be non-empty")
    ids: set[str] = set()
    metrics: set[str] = set()
    for index, gate in enumerate(gates):
        if not isinstance(gate, dict) or set(gate) != GATE_FIELDS:
            raise TaskGateContractError(f"gate {index} fields invalid")
        gate_id = gate["id"]
        if not isinstance(gate_id, str) or not ID_RE.fullmatch(gate_id) or gate_id in ids:
            raise TaskGateContractError(f"gate {index} id invalid or duplicated")
        ids.add(gate_id)
        if not isinstance(gate["name"], str) or not gate["name"].strip():
            raise TaskGateContractError(f"gate {gate_id} name invalid")
        argv = gate["argv"]
        if not isinstance(argv, list) or not argv or any(not isinstance(part, str) or not part for part in argv):
            raise TaskGateContractError(f"gate {gate_id} argv invalid")
        if argv[0] in {"true", "false", "echo"}:
            raise TaskGateContractError(f"gate {gate_id} placeholder command")
        if argv[0] in {"sh", "bash", "python", "python3"} and len(argv) > 1 and argv[1] in {"-c", "-e"}:
            raise TaskGateContractError(f"gate {gate_id} shell wrapper is forbidden")
        if any(any(char in part for char in ";&|<>$`\n\r") for part in argv):
            raise TaskGateContractError(f"gate {gate_id} shell operator is forbidden")
        if not isinstance(gate["command"], str) or gate["command"] != shlex.join(argv):
            raise TaskGateContractError(f"gate {gate_id} command does not match argv")
        env = gate["env"]
        if not isinstance(env, dict) or any(
            not isinstance(key, str) or not isinstance(val, str) for key, val in env.items()
        ):
            raise TaskGateContractError(f"gate {gate_id} env invalid")
        _canonical_cwd(gate["cwd"])
        if gate["parser"] not in PARSERS:
            raise TaskGateContractError(f"gate {gate_id} parser invalid")
        metric = gate["metric"]
        if gate["parser"] == "exit":
            if metric is not None:
                raise TaskGateContractError(f"gate {gate_id} exit parser cannot have metric")
        elif not isinstance(metric, str) or not metric or metric in metrics:
            raise TaskGateContractError(f"gate {gate_id} metric invalid or duplicated")
        else:
            metrics.add(metric)
        if not isinstance(gate["timeout_seconds"], int) or not 1 <= gate["timeout_seconds"] <= 7200:
            raise TaskGateContractError(f"gate {gate_id} timeout invalid")
        if not isinstance(gate["max_output_bytes"], int) or not 1024 <= gate["max_output_bytes"] <= 16777216:
            raise TaskGateContractError(f"gate {gate_id} output limit invalid")
    return value


def contract_sha256(contract: dict) -> str:
    validate_contract(contract)
    canonical = json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(canonical).hexdigest()


def contract_identity(contract: dict) -> dict:
    validate_contract(contract)
    return {
        "project_id": contract["project_id"],
        "task_id": contract["task_id"],
        "task_sha256": contract["task_sha256"],
        "contract_sha256": contract_sha256(contract),
    }


def validate_gate_run_identity(gate_run: dict, contract: dict) -> None:
    if gate_run.get("task_gate_contract") != contract_identity(contract):
        raise TaskGateContractError("TASK_GATE_CONTRACT_MISMATCH: gate-run contract identity mismatch")


def manifest_gates(contract: dict) -> list[dict]:
    validate_contract(contract)
    return [
        {
            "id": gate["id"],
            "name": gate["name"],
            "kind": "command",
            "argv": list(gate["argv"]),
            "env": dict(gate["env"]),
            "timeout_seconds": gate["timeout_seconds"],
            "max_output_bytes": gate["max_output_bytes"],
        }
        for gate in contract["required_gates"]
    ]


def gate_plan(contract: dict) -> dict:
    validate_contract(contract)
    return {
        "schema_version": 1,
        "gates": [
            {
                "id": gate["id"],
                "steps": [
                    {
                        "id": gate["id"],
                        "argv": list(gate["argv"]),
                        "env": dict(gate["env"]),
                        "cwd": gate["cwd"],
                        "parser": gate["parser"],
                        "metric": gate["metric"],
                        "timeout_seconds": gate["timeout_seconds"],
                        "max_output_bytes": gate["max_output_bytes"],
                    }
                ],
            }
            for gate in contract["required_gates"]
        ],
    }


def atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with open(fd, "w", encoding="utf-8", closefd=True) as stream:
            json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
        Path(temporary).replace(path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def validate_generated_outputs(contract: dict, manifest: dict, plan: dict) -> None:
    expected_manifest = manifest_gates(contract)
    if manifest.get("gates") != expected_manifest:
        raise TaskGateContractError("TASK_GATE_CONTRACT_MISMATCH: manifest gates diverge")
    expected_plan = gate_plan(contract)
    if plan != expected_plan:
        raise TaskGateContractError("TASK_GATE_CONTRACT_MISMATCH: gate plan diverges")
