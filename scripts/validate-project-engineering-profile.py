#!/usr/bin/env python3
"""Validate a target project's engineering profile against a pinned planner."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


class ProfileError(ValueError):
    pass


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"invalid JSON {path}: {exc}") from exc


def control_free(value: str) -> bool:
    return all(ord(c) >= 0x20 and ord(c) != 0x7F for c in value)


def validate(declaration_path: Path, project_root: Path, planner_root: Path, allow_missing: bool, now: datetime) -> str:
    if not declaration_path.exists():
        if allow_missing:
            print(f"PASS: engineering profile missing (allowed): {declaration_path}")
            return "missing"
        raise ProfileError(f"missing declaration: {declaration_path}")
    data = load(declaration_path)
    allowed = {"schema_version", "workflow_lock_path", "profile_id", "exceptions"}
    if not isinstance(data, dict) or set(data) - allowed or data.get("schema_version") != 1:
        raise ProfileError("declaration schema or unknown field invalid")
    lock_path = data.get("workflow_lock_path")
    if not isinstance(lock_path, str) or not lock_path or Path(lock_path).is_absolute() or ".." in Path(lock_path).parts or not control_free(lock_path):
        raise ProfileError("workflow_lock_path must be a normalized relative path")
    profile_id = data.get("profile_id")
    if not isinstance(profile_id, str) or not ID_RE.fullmatch(profile_id):
        raise ProfileError("profile_id is invalid")
    exceptions = data.get("exceptions")
    if not isinstance(exceptions, list):
        raise ProfileError("exceptions must be an array")
    lock = load(project_root / lock_path)
    for key in ("repository", "version", "commit", "document"):
        if not isinstance(lock.get(key), str) or not lock[key] or not control_free(lock[key]):
            raise ProfileError(f"lock field invalid: {key}")
    try:
        planner_commit = subprocess.run(["git", "-C", str(planner_root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ProfileError(f"unable to resolve planner checkout: {exc}") from exc
    if re.fullmatch(r"[0-9a-fA-F]{40}", planner_commit) and lock["commit"] != planner_commit:
        raise ProfileError("workflow lock commit does not match planner checkout")
    catalog = load(planner_root / "profiles/engineering/catalog.json")
    rules = load(planner_root / "profiles/engineering/rules.json")
    rule_map = {r["id"]: r for r in rules["rules"]}
    entry = next((p for p in catalog["profiles"] if p["profile_id"] == profile_id), None)
    if entry is None:
        raise ProfileError(f"unknown profile: {profile_id}")
    profile = load(planner_root / entry["definition"])
    for item in exceptions:
        if not isinstance(item, dict) or set(item) - {"id","rule_id","reason","scope","approved_by","migration_target","migration_required","expires_at"}:
            raise ProfileError("exception schema or unknown field invalid")
        if not isinstance(item.get("id"), str) or not ID_RE.fullmatch(item["id"]):
            raise ProfileError("exception id invalid")
        if not all(isinstance(item.get(k), str) and item[k].strip() and control_free(item[k]) for k in ("rule_id","reason","scope","approved_by")):
            raise ProfileError("exception text fields must be non-empty")
        rule = rule_map.get(item["rule_id"])
        if rule is None or not rule["exception_allowed"]:
            raise ProfileError(f"exception rule is unknown or not exception-capable: {item['rule_id']}")
        expiry = item.get("expires_at")
        if expiry is not None:
            if not isinstance(expiry, str) or not RFC3339.fullmatch(expiry):
                raise ProfileError("expires_at must be UTC RFC3339 or null")
            if datetime.fromisoformat(expiry.replace("Z", "+00:00")) <= now:
                raise ProfileError(f"exception expired: {item['id']}")
    ids = [item["id"] for item in exceptions]
    if len(ids) != len(set(ids)):
        raise ProfileError("exception IDs must be unique")
    print(f"PASS: engineering profile {profile_id} ({len(exceptions)} exceptions)")
    return profile["profile_id"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("declaration", type=Path)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--planner-root", type=Path, required=True)
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--now", help="UTC RFC3339 time for deterministic tests")
    args = parser.parse_args()
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else datetime.now(timezone.utc)
    try:
        validate(args.declaration, args.project_root, args.planner_root, args.allow_missing, now)
    except (ProfileError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
