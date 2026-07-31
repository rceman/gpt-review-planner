"""Strict project execution-mode lookup shared by evidence tools."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def project_execution_mode(repo: Path) -> str:
    lock = repo / ".gpt-workflow.lock"
    try:
        data = json.loads(lock.read_text(encoding="utf-8"), object_pairs_hook=_unique)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid .gpt-workflow.lock: {exc}") from exc
    if not isinstance(data, dict) or set(data) != {"schema_version", "repository", "version", "commit", "document", "execution_mode", "installed_at"}:
        raise ValueError(".gpt-workflow.lock must declare exactly one execution_mode")
    if data.get("schema_version") != 2:
        raise ValueError(".gpt-workflow.lock schema_version must be 2")
    mode = data.get("execution_mode")
    if mode not in {"gpt_tunnel_managed", "repository_evidence"}:
        raise ValueError("execution_mode must be explicit")
    return mode


def require_repository_evidence(repo: Path) -> None:
    if project_execution_mode(repo) != "repository_evidence":
        raise ValueError("repository evidence is forbidden in gpt_tunnel_managed mode")
