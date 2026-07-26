#!/usr/bin/env python3
"""Validate the versioned engineering rules, sources, schemas, and profiles."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[A-Z][A-Z0-9-]+-[0-9]{3}$")
ANCHOR_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PROFILE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SELECTOR_RE = re.compile(r"^(all-projects|profile:[a-z0-9]+(?:-[a-z0-9]+)*|capability:[a-z0-9]+(?:-[a-z0-9]+)*)$")
LEVELS = {"must", "must_not", "should", "should_not", "may"}
CATEGORIES = {"stack", "language", "framework", "database", "api", "security", "performance", "configuration", "observability", "testing", "dependency", "template", "exception", "structure"}
CAPABILITIES = {"frontend", "backend-rust", "backend-go", "backend-python", "postgresql", "liquibase", "generated-contracts", "health-readiness", "graceful-shutdown", "observability", "tests", "accessibility", "deterministic-tests", "isolated-fixtures", "safe-config", "secure-config"}
OFFICIAL_SOURCE_DOMAINS = {"doc.rust-lang.org", "rust-lang.github.io", "tokio.rs", "docs.rs", "go.dev", "gin-gonic.com", "pkg.go.dev", "docs.sqlc.dev", "docs.python.org", "peps.python.org", "packaging.python.org", "docs.pytest.org", "docs.astral.sh", "microsoft.github.io", "typescriptlang.org", "svelte.dev", "postgresql.org", "docs.liquibase.com", "liquibase.com", "owasp.org", "opentelemetry.io", "spec.openapis.org", "json-schema.org"}


class CatalogError(ValueError):
    pass


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CatalogError(f"invalid JSON {path}: {exc}") from exc


def control_free(value: str) -> bool:
    return all(ord(c) >= 0x20 and ord(c) != 0x7F for c in value)


def safe_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or value.startswith(("/", "\\")) or re.match(r"^(?:[A-Za-z]:|file://|\\\\)", value, re.I):
        raise CatalogError(f"{label} must be a portable relative path")
    parts = Path(value).parts
    if ".." in parts or value in {".", ".."} or "//" in value or "\\" in value or any(ord(c) < 0x20 or ord(c) == 0x7F for c in value):
        raise CatalogError(f"{label} contains traversal, backslash, or control characters")
    return value


def string_array(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value) or any(not isinstance(x, str) or not x or not control_free(x) for x in value):
        raise CatalogError(f"{label} must be a string array")
    return value


def explicit_anchor(text: str, anchor: str) -> bool:
    return len(re.findall(rf'<a\s+id="{re.escape(anchor)}"></a>', text)) == 1


def validate_schema_files(root: Path) -> None:
    for path in (root / "schemas").glob("*engineering*.schema.json"):
        data = load(path)
        if not isinstance(data, dict) or not str(data.get("$schema", "")).startswith("https://json-schema.org/") or data.get("type") != "object":
            raise CatalogError(f"schema identity invalid: {path}")
        if not isinstance(data.get("required"), list) or any(not isinstance(x, str) for x in data["required"]):
            raise CatalogError(f"schema required list invalid: {path}")
    declaration = load(root / "schemas/project-engineering-declaration.schema.json")
    if not isinstance(declaration, dict) or not str(declaration.get("$schema", "")).startswith("https://json-schema.org/"):
        raise CatalogError("declaration schema identity invalid")
    declaration_fields = {"schema_version", "workflow_lock_path", "profile_id", "exceptions"}
    if set(declaration.get("required", [])) != declaration_fields or set(declaration.get("properties", {})) != declaration_fields or declaration.get("additionalProperties") is not False:
        raise CatalogError("declaration schema field parity invalid")
    exception_schema = declaration["properties"]["exceptions"]["items"]
    exception_fields = {"id", "rule_id", "reason", "scope", "approved_by", "migration_target", "migration_required", "expires_at"}
    if set(exception_schema.get("required", [])) != exception_fields or set(exception_schema.get("properties", {})) != exception_fields or exception_schema.get("additionalProperties") is not False:
        raise CatalogError("exception schema field parity invalid")
    example = load(root / "templates/project/engineering-profile.example.json")
    if set(example) != declaration_fields or example.get("schema_version") != 1 or not isinstance(example.get("workflow_lock_path"), str) or not isinstance(example.get("profile_id"), str) or not isinstance(example.get("exceptions"), list):
        raise CatalogError("engineering profile example does not match declaration contract")


def validate_sources(root: Path, today: date) -> None:
    registry = load(root / "profiles/engineering/source-metadata.json")
    if registry.get("schema_version") != 1 or not isinstance(registry.get("documents"), list):
        raise CatalogError("source metadata registry is invalid")
    seen: set[str] = set()
    for entry in registry["documents"]:
        if not isinstance(entry, dict) or set(entry) != {"document", "last_reviewed", "source_domains"}:
            raise CatalogError("source metadata entry has unknown or missing fields")
        document = safe_path(entry["document"], "source document")
        if document in seen or not (root / document).is_file():
            raise CatalogError(f"duplicate or missing source document: {document}")
        seen.add(document)
        try:
            reviewed = date.fromisoformat(entry["last_reviewed"])
        except (TypeError, ValueError) as exc:
            raise CatalogError(f"invalid last_reviewed for {document}") from exc
        if reviewed > today:
            raise CatalogError(f"future last_reviewed for {document}")
        domains = string_array(entry["source_domains"], f"{document}.source_domains", allow_empty=False)
        if len(domains) != len(set(domains)) or any(not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", domain) or domain not in OFFICIAL_SOURCE_DOMAINS for domain in domains):
            raise CatalogError(f"invalid or non-approved source domain: {document}")
        text = (root / document).read_text(encoding="utf-8")
        if "## Primary sources" not in text:
            raise CatalogError(f"missing Primary sources section: {document}")
        if any(domain not in text for domain in domains):
            raise CatalogError(f"source domains are not all represented in Primary sources: {document}")
    expected = set()
    for folder in ("languages", "frameworks", "database"):
        expected |= {str(p.relative_to(root)) for p in (root / "docs/engineering" / folder).glob("*.md")}
    for path in ("DEPENDENCY_POLICY.md", "PERFORMANCE_BASELINE.md", "SECURITY_BASELINE.md", "CONFIGURATION_AND_SECRETS.md", "OBSERVABILITY.md", "API_CONTRACTS.md", "TESTING_BASELINE.md"):
        expected.add(f"docs/engineering/{path}")
    if expected != seen:
        raise CatalogError(f"source metadata coverage mismatch: missing={sorted(expected-seen)} extra={sorted(seen-expected)}")


def validate(root: Path, today: date | None = None) -> tuple[int, int]:
    today = today or date.today()
    validate_schema_files(root)
    validate_sources(root, today)
    rules_data = load(root / "profiles/engineering/rules.json")
    catalog = load(root / "profiles/engineering/catalog.json")
    if set(rules_data) != {"schema_version", "rules"} or set(catalog) != {"schema_version", "catalog_id", "rules_file", "profiles"} or catalog.get("catalog_id") != "rceman-engineering-baseline" or rules_data.get("schema_version") != 1 or catalog.get("schema_version") != 1:
        raise CatalogError("schema_version must equal 1")
    if catalog.get("rules_file") != "profiles/engineering/rules.json":
        raise CatalogError("catalog rules_file must name the canonical rules file")
    rules = rules_data.get("rules")
    if not isinstance(rules, list):
        raise CatalogError("rules must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    anchors: set[str] = set()
    for rule in rules:
        required_keys = {"id","level","title","category","document","anchor","applies_to","exception_allowed","replacement","deprecated"}
        if not isinstance(rule, dict) or set(rule) != required_keys:
            raise CatalogError("rule has missing or unknown fields")
        rid = rule["id"]
        if not isinstance(rid, str) or not ID_RE.fullmatch(rid) or rid in by_id:
            raise CatalogError(f"invalid or duplicate rule id: {rid!r}")
        if rule["level"] not in LEVELS or rule["category"] not in CATEGORIES:
            raise CatalogError(f"invalid level/category for {rid}")
        document = safe_path(rule["document"], f"{rid}.document")
        anchor = rule["anchor"]
        if not isinstance(anchor, str) or not ANCHOR_RE.fullmatch(anchor):
            raise CatalogError(f"anchor must be lowercase kebab-case for {rid}")
        if anchor in anchors:
            raise CatalogError(f"duplicate explicit anchor: {anchor}")
        anchors.add(anchor)
        applies = string_array(rule["applies_to"], f"{rid}.applies_to", allow_empty=False)
        for selector in applies:
            if not SELECTOR_RE.fullmatch(selector):
                raise CatalogError(f"invalid applicability selector for {rid}: {selector}")
        if not isinstance(rule["title"], str) or not rule["title"].strip() or not control_free(rule["title"]):
            raise CatalogError(f"invalid title for {rid}")
        if type(rule["exception_allowed"]) is not bool or type(rule["deprecated"]) is not bool:
            raise CatalogError(f"boolean field invalid for {rid}")
        replacement = rule["replacement"]
        if replacement is not None and (not isinstance(replacement, str) or replacement == rid):
            raise CatalogError(f"invalid replacement for {rid}")
        path = root / document
        if not path.is_file() or not explicit_anchor(path.read_text(encoding="utf-8"), anchor):
            raise CatalogError(f"missing or duplicate explicit anchor: {document}#{anchor}")
        by_id[rid] = rule
    for rid, rule in by_id.items():
        replacement = rule["replacement"]
        if replacement and replacement not in by_id:
            raise CatalogError(f"replacement for {rid} is unknown")
        seen: set[str] = set(); current = rid
        while by_id[current]["replacement"]:
            if current in seen:
                raise CatalogError(f"replacement cycle at {rid}")
            seen.add(current); current = by_id[current]["replacement"]
    profiles = catalog.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise CatalogError("profiles must be a non-empty array")
    profile_ids: set[str] = set(); definitions: set[str] = set(); capabilities: set[str] = set(); profile_data: dict[str, dict[str, Any]] = {}
    for entry in profiles:
        if not isinstance(entry, dict) or set(entry) != {"profile_id","kind","document","definition"}:
            raise CatalogError("catalog profile has missing or unknown fields")
        pid = entry["profile_id"]
        if not isinstance(pid, str) or not PROFILE_RE.fullmatch(pid) or pid in profile_ids:
            raise CatalogError(f"invalid or duplicate profile id: {pid!r}")
        if entry["kind"] != "project":
            raise CatalogError(f"invalid profile kind: {pid}")
        profile_ids.add(pid); definitions.add(entry["definition"])
        doc = safe_path(entry["document"], f"{pid}.document"); definition = safe_path(entry["definition"], f"{pid}.definition")
        if not (root / doc).is_file() or not (root / definition).is_file():
            raise CatalogError(f"missing profile document/definition: {pid}")
        data = load(root / definition)
        required_profile_keys = {"schema_version","profile_id","title","project_kind","capabilities","non_capabilities","required_rule_ids","recommended_rule_ids","forbidden_rule_ids","language_documents","framework_documents","database_documents","review_checklists","template_contract"}
        if set(data) != required_profile_keys or data.get("schema_version") != 1 or data.get("profile_id") != pid:
            raise CatalogError(f"profile schema or identity mismatch: {pid}")
        profile_data[pid] = data
        caps = set(string_array(data["capabilities"], f"{pid}.capabilities", allow_empty=False)); noncaps = set(string_array(data["non_capabilities"], f"{pid}.non_capabilities"))
        if caps & noncaps or not caps <= CAPABILITIES or not noncaps <= CAPABILITIES:
            raise CatalogError(f"invalid or conflicting capabilities: {pid}")
        capabilities |= caps
        lists = {"required_rule_ids":data["required_rule_ids"],"recommended_rule_ids":data["recommended_rule_ids"],"forbidden_rule_ids":data["forbidden_rule_ids"]}
        all_refs: set[str] = set()
        for name, values in lists.items():
            values = string_array(values, f"{pid}.{name}")
            if all_refs & set(values):
                raise CatalogError(f"duplicate rule reference across lists: {pid}")
            all_refs |= set(values)
            expected = "must" if name == "required_rule_ids" else "must_not" if name == "forbidden_rule_ids" else {"should","should_not","may"}
            for ref in values:
                if ref not in by_id or (by_id[ref]["level"] != expected if isinstance(expected, str) else by_id[ref]["level"] not in expected):
                    raise CatalogError(f"rule level/list mismatch or unknown rule: {pid}/{name}/{ref}")
        for key in ("language_documents", "framework_documents", "database_documents", "review_checklists"):
            for value in string_array(data[key], f"{pid}.{key}"):
                if not (root / safe_path(value, f"{pid}.{key}")).is_file():
                    raise CatalogError(f"missing referenced document in {pid}: {value}")
        contract = data["template_contract"]
        if not isinstance(contract, dict) or set(contract) != {"required_paths","forbidden_paths","required_capabilities","forbidden_capabilities"}:
            raise CatalogError(f"invalid template contract: {pid}")
        for key in ("required_paths", "forbidden_paths"):
            for value in string_array(contract[key], f"{pid}.{key}"):
                safe_path(value, f"{pid}.{key}")
        required_caps = set(string_array(contract["required_capabilities"], f"{pid}.required_capabilities")); forbidden_caps = set(string_array(contract["forbidden_capabilities"], f"{pid}.forbidden_capabilities"))
        if required_caps & forbidden_caps or not required_caps <= CAPABILITIES or not forbidden_caps <= CAPABILITIES:
            raise CatalogError(f"invalid template capabilities: {pid}")
        if not required_caps <= caps:
            raise CatalogError(f"template capabilities not declared by profile: {pid}")
    for rule in by_id.values():
        for selector in rule["applies_to"]:
            if selector.startswith("profile:") and selector.split(":", 1)[1] not in profile_ids:
                raise CatalogError(f"unknown profile selector: {selector}")
            if selector.startswith("capability:") and selector.split(":", 1)[1] not in CAPABILITIES:
                raise CatalogError(f"unknown capability selector: {selector}")
    for pid, data in profile_data.items():
        selectors = {"all-projects", f"profile:{pid}"} | {f"capability:{cap}" for cap in data["capabilities"]}
        applicable = [rule for rule in by_id.values() if selectors.intersection(rule["applies_to"])]
        required = set(data["required_rule_ids"])
        forbidden = set(data["forbidden_rule_ids"])
        missing_must = {rule["id"] for rule in applicable if rule["level"] == "must"} - required
        missing_must_not = {rule["id"] for rule in applicable if rule["level"] == "must_not"} - forbidden
        if missing_must or missing_must_not:
            raise CatalogError(f"incomplete applicable rule coverage for {pid}: must={sorted(missing_must)} must_not={sorted(missing_must_not)}")
    orphan = {str(p.relative_to(root)) for p in (root / "profiles/engineering/projects").glob("*.json")} - definitions
    if orphan:
        raise CatalogError(f"orphan profile definitions: {sorted(orphan)}")
    return len(by_id), len(profile_ids)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--today", help="ISO date for deterministic freshness tests")
    args = parser.parse_args()
    try:
        rules, profiles = validate(args.repository_root.resolve(), date.fromisoformat(args.today) if args.today else None)
    except (CatalogError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1
    print(f"PASS: engineering catalog ({rules} rules, {profiles} profiles)"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
