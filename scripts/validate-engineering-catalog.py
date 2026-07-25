#!/usr/bin/env python3
"""Validate the versioned engineering rule registry and project catalog."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[A-Z][A-Z0-9-]+-[0-9]{3}$")
PROFILE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LEVELS = {"must", "must_not", "should", "should_not", "may"}
CATEGORIES = {"stack", "language", "framework", "database", "api", "security", "performance", "configuration", "observability", "testing", "dependency", "template", "exception", "structure"}


class CatalogError(ValueError):
    pass


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CatalogError(f"invalid JSON {path}: {exc}") from exc


def safe_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", value):
        raise CatalogError(f"{label} must be a relative path")
    if ".." in Path(value).parts or any(ord(c) < 0x20 or ord(c) == 0x7F for c in value):
        raise CatalogError(f"{label} contains traversal or control characters")
    if "main" in value and ("http" in value or "workflow" in value):
        raise CatalogError(f"{label} contains a mutable workflow reference")
    return value


def strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x for x in value):
        raise CatalogError(f"{label} must be a non-empty string array")
    return value


def validate(root: Path) -> tuple[int, int]:
    rules_data = load(root / "profiles/engineering/rules.json")
    catalog = load(root / "profiles/engineering/catalog.json")
    if rules_data.get("schema_version") != 1 or catalog.get("schema_version") != 1:
        raise CatalogError("schema_version must equal 1")
    rules = rules_data.get("rules")
    if not isinstance(rules, list):
        raise CatalogError("rules must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            raise CatalogError("each rule must be an object")
        rid = rule.get("id")
        if not isinstance(rid, str) or not ID_RE.fullmatch(rid) or rid in by_id:
            raise CatalogError(f"invalid or duplicate rule id: {rid!r}")
        if rule.get("level") not in LEVELS or rule.get("category") not in CATEGORIES:
            raise CatalogError(f"invalid level/category for {rid}")
        document = safe_path(rule.get("document"), f"{rid}.document")
        anchor = rule.get("anchor")
        if not isinstance(anchor, str) or not anchor or any(ord(c) < 0x20 or ord(c) == 0x7F for c in anchor):
            raise CatalogError(f"invalid anchor for {rid}")
        applies = strings(rule.get("applies_to"), f"{rid}.applies_to")
        if not isinstance(rule.get("title"), str) or not rule["title"].strip():
            raise CatalogError(f"empty title for {rid}")
        if type(rule.get("exception_allowed")) is not bool or type(rule.get("deprecated")) is not bool:
            raise CatalogError(f"boolean field invalid for {rid}")
        replacement = rule.get("replacement")
        if replacement is not None and (not isinstance(replacement, str) or replacement == rid):
            raise CatalogError(f"invalid replacement for {rid}")
        path = root / document
        if not path.is_file() or anchor not in path.read_text(encoding="utf-8"):
            raise CatalogError(f"missing document or anchor for {rid}: {document}#{anchor}")
        by_id[rid] = {**rule, "applies_to": applies}
    for rid, rule in by_id.items():
        replacement = rule.get("replacement")
        if replacement and replacement not in by_id:
            raise CatalogError(f"replacement for {rid} is unknown")
        seen: set[str] = set()
        current = rid
        while by_id[current].get("replacement"):
            if current in seen:
                raise CatalogError(f"replacement cycle at {rid}")
            seen.add(current)
            current = by_id[current]["replacement"]
    profiles = catalog.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise CatalogError("profiles must be a non-empty array")
    profile_ids: set[str] = set()
    for entry in profiles:
        if not isinstance(entry, dict):
            raise CatalogError("catalog profile must be an object")
        pid = entry.get("profile_id")
        if not isinstance(pid, str) or not PROFILE_RE.fullmatch(pid) or pid in profile_ids:
            raise CatalogError(f"invalid or duplicate profile id: {pid!r}")
        if entry.get("kind") != "project":
            raise CatalogError(f"invalid profile kind: {pid}")
        profile_ids.add(pid)
        doc = safe_path(entry.get("document"), f"{pid}.document")
        definition = safe_path(entry.get("definition"), f"{pid}.definition")
        if not (root / doc).is_file() or not (root / definition).is_file():
            raise CatalogError(f"missing profile document/definition: {pid}")
        data = load(root / definition)
        if data.get("schema_version") != 1 or data.get("profile_id") != pid:
            raise CatalogError(f"profile definition identity mismatch: {pid}")
        required = set(strings(data.get("required_rule_ids"), f"{pid}.required_rule_ids")) if data.get("required_rule_ids") else set()
        recommended = set(data.get("recommended_rule_ids", []))
        forbidden = set(data.get("forbidden_rule_ids", []))
        all_refs = required | recommended | forbidden
        if not all(isinstance(x, str) and x in by_id for x in all_refs):
            raise CatalogError(f"unknown rule in profile: {pid}")
        if required & forbidden:
            raise CatalogError(f"required/forbidden rule conflict: {pid}")
        for key in ("language_documents", "framework_documents", "database_documents", "review_checklists"):
            for value in data.get(key, []):
                if not (isinstance(value, str) and (root / safe_path(value, f"{pid}.{key}")).is_file()):
                    raise CatalogError(f"missing referenced document in {pid}: {value}")
        contract = data.get("template_contract")
        if not isinstance(contract, dict):
            raise CatalogError(f"missing template contract: {pid}")
        for key in ("required_paths", "forbidden_paths", "required_capabilities", "forbidden_capabilities"):
            if not isinstance(contract.get(key), list) or any(not isinstance(x, str) for x in contract[key]):
                raise CatalogError(f"invalid template contract {pid}.{key}")
    return len(by_id), len(profile_ids)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        rules, profiles = validate(args.repository_root.resolve())
    except CatalogError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: engineering catalog ({rules} rules, {profiles} profiles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
