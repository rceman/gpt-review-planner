#!/usr/bin/env python3
"""Validate a target project's engineering profile against a pinned planner."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
WORKFLOW_VERSION_RE = re.compile(r"^(?:v\d+\.\d+\.\d+|[0-9a-f]{40})$", re.IGNORECASE)
EXCEPTION_KEYS = {"id", "rule_id", "reason", "scope", "approved_by", "migration_target", "migration_required", "expires_at"}


class ProfileError(ValueError):
    pass


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"invalid JSON {path}: {exc}") from exc


def control_free(value: str) -> bool:
    return all(ord(c) >= 0x20 and ord(c) != 0x7F for c in value)


def safe_relative_path(value: Any, label: str, root: Path) -> Path:
    if not isinstance(value, str) or not value or value != value.strip() or not control_free(value):
        raise ProfileError(f"{label} must be a normalized relative path")
    lowered = value.lower()
    if lowered.startswith("file:") or value.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", value) or value.startswith("\\\\"):
        raise ProfileError(f"{label} must be a normalized relative path")
    if "\\" in value or "//" in value or value in {".", ".."} or ".." in Path(value).parts:
        raise ProfileError(f"{label} must be a normalized relative path")
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ProfileError(f"{label} escapes project root") from exc
    return candidate


def strict_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or not control_free(value):
        raise ProfileError(f"{label} must be non-empty trimmed text")
    return value


def parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not RFC3339.fullmatch(value):
        raise ProfileError(f"{label} must be UTC RFC3339")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ProfileError(f"{label} must be UTC RFC3339")
    return parsed


def validate_planner_catalog(planner_root: Path) -> tuple[int, int]:
    validator_path = planner_root / "scripts/validate-engineering-catalog.py"
    spec = importlib.util.spec_from_file_location("engineering_catalog_validator", validator_path)
    if spec is None or spec.loader is None:
        raise ProfileError("planner catalog validator is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        return module.validate(planner_root)
    except Exception as exc:
        raise ProfileError(f"planner catalog is invalid: {exc}") from exc


def validate(declaration_path: Path, project_root: Path, planner_root: Path, allow_missing: bool, now: datetime) -> str:
    declaration_path = declaration_path.resolve()
    project_root = project_root.resolve()
    planner_root = planner_root.resolve()
    try:
        declaration_path.relative_to(project_root)
    except ValueError as exc:
        raise ProfileError("declaration path must resolve inside project root") from exc
    if not declaration_path.exists():
        if allow_missing:
            print("PASS: engineering profile missing (allowed)")
            return "missing"
        raise ProfileError(f"missing declaration: {declaration_path}")
    data = load(declaration_path)
    allowed = {"schema_version", "workflow_lock_path", "profile_id", "exceptions"}
    if not isinstance(data, dict) or set(data) - allowed or data.get("schema_version") != 1:
        raise ProfileError("declaration schema or unknown field invalid")
    lock_path = data.get("workflow_lock_path")
    lock_file = safe_relative_path(lock_path, "workflow_lock_path", project_root)
    profile_id = data.get("profile_id")
    if not isinstance(profile_id, str) or not ID_RE.fullmatch(profile_id):
        raise ProfileError("profile_id is invalid")
    exceptions = data.get("exceptions")
    if not isinstance(exceptions, list):
        raise ProfileError("exceptions must be an array")
    lock = load(lock_file)
    required_lock = {"schema_version", "repository", "version", "commit", "document", "installed_at"}
    if not isinstance(lock, dict) or set(lock) != required_lock or lock.get("schema_version") != 1:
        raise ProfileError("workflow lock schema or fields invalid")
    for key in ("repository", "version", "document"):
        strict_text(lock[key], f"lock.{key}")
    parse_utc(lock["installed_at"], "lock.installed_at")
    if lock["repository"].rstrip("/") not in {"https://github.com/rceman/gpt-review-planner", "git@github.com:rceman/gpt-review-planner.git"}:
        raise ProfileError("lock.repository identity is invalid")
    if not WORKFLOW_VERSION_RE.fullmatch(lock["version"]):
        raise ProfileError("lock.version must be a version tag or exact 40-character commit")
    if not COMMIT_RE.fullmatch(lock["commit"]):
        raise ProfileError("lock.commit must be a 40-character lowercase commit")
    planner_document = safe_relative_path(lock["document"], "lock.document", planner_root)
    if not planner_document.is_file():
        raise ProfileError("lock.document does not exist in planner checkout")
    try:
        planner_commit = subprocess.run(["git", "-C", str(planner_root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ProfileError(f"unable to resolve planner checkout: {exc}") from exc
    if not COMMIT_RE.fullmatch(planner_commit) or lock["commit"] != planner_commit:
        raise ProfileError("workflow lock commit does not match planner checkout")
    validate_planner_catalog(planner_root)
    catalog = load(planner_root / "profiles/engineering/catalog.json")
    rules = load(planner_root / "profiles/engineering/rules.json")
    rule_map = {r["id"]: r for r in rules["rules"]}
    entry = next((p for p in catalog["profiles"] if p["profile_id"] == profile_id), None)
    if entry is None:
        raise ProfileError(f"unknown profile: {profile_id}")
    profile = load(planner_root / entry["definition"])
    capabilities = set(profile.get("capabilities", []))
    for item in exceptions:
        if not isinstance(item, dict) or set(item) != EXCEPTION_KEYS:
            raise ProfileError("exception schema or unknown field invalid")
        if not isinstance(item.get("id"), str) or not ID_RE.fullmatch(item["id"]):
            raise ProfileError("exception id invalid")
        for key in ("rule_id", "reason", "scope", "approved_by"):
            strict_text(item.get(key), f"exception.{key}")
        if item["migration_target"] is not None:
            strict_text(item["migration_target"], "exception.migration_target")
        if type(item["migration_required"]) is not bool:
            raise ProfileError("exception.migration_required must be boolean")
        rule = rule_map.get(item["rule_id"])
        if rule is None or not rule["exception_allowed"]:
            raise ProfileError(f"exception rule is unknown or not exception-capable: {item['rule_id']}")
        selectors = rule["applies_to"]
        if "all-projects" not in selectors and f"profile:{profile_id}" not in selectors and not any(s.startswith("capability:") and s.split(":", 1)[1] in capabilities for s in selectors):
            raise ProfileError(f"exception rule is not applicable to profile: {item['rule_id']}")
        expiry = item.get("expires_at")
        if expiry is not None:
            parsed_expiry = parse_utc(expiry, "expires_at")
            if parsed_expiry <= now:
                raise ProfileError(f"exception expired: {item['id']}")
    ids = [item["id"] for item in exceptions]
    if len(ids) != len(set(ids)):
        raise ProfileError("exception IDs must be unique")
    print(f"PASS: profile={profile_id} capabilities={','.join(sorted(capabilities))} exceptions={len(exceptions)} exception_ids={','.join(ids) or '-'} exception_rule_ids={','.join(item['rule_id'] for item in exceptions) or '-'} planner_commit={planner_commit}")
    return profile["profile_id"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("declaration", type=Path)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--planner-root", type=Path, required=True)
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--now", help="UTC RFC3339 time for deterministic tests")
    args = parser.parse_args()
    now = parse_utc(args.now, "--now") if args.now else datetime.now(timezone.utc)
    try:
        validate(args.declaration, args.project_root, args.planner_root, args.allow_missing, now)
    except (ProfileError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
