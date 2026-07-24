#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REQUIRED_FILES = (
    "README_FIRST.md",
    "AGENT_PROMPT.md",
    "PATCH_SPEC.md",
    "BEHAVIOR_CONTRACT.md",
    "VALIDATION_REPORT.md",
    "manifest.json",
    "evidence.json",
    "scripts/patch_pack_scope.py",
    "scripts/verify-agent-evidence.py",
    "scripts/verify-agent-result.sh",
    "expected/acceptance-gates.md",
    "expected/allowed-deviations.md",
)
PATCH_ID_RE = re.compile(r"^patch-(\d{8}-\d{6})-([a-z0-9]+(?:-[a-z0-9]+){0,2})$")
BASELINE_RE = re.compile(r"^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def validate_identity(manifest: dict[str, object], errors: list[str]) -> None:
    if manifest.get("schema_version") != 2:
        errors.append("manifest schema_version must be 2")
    patch_id = str(manifest.get("patch_id", ""))
    match = PATCH_ID_RE.fullmatch(patch_id)
    if not match:
        errors.append("manifest patch_id must be patch-YYYYMMDD-HHMMSS-<1-to-3-word-slug>")
        return
    timestamp = str(manifest.get("patch_timestamp", ""))
    slug = str(manifest.get("patch_slug", ""))
    baseline = str(manifest.get("baseline_release", ""))
    created_at = str(manifest.get("created_at", ""))
    evidence = str(manifest.get("evidence_directory", ""))
    title = str(manifest.get("title", ""))
    description = str(manifest.get("description", ""))
    if timestamp != match.group(1) or slug != match.group(2):
        errors.append("manifest timestamp/slug must match patch_id")
    if not BASELINE_RE.fullmatch(baseline):
        errors.append("manifest baseline_release must be a v-prefixed semantic version")
    expected = f".gpt-review/evidence/{baseline}/{patch_id}"
    if evidence != expected:
        errors.append(f"manifest evidence_directory must equal {expected}")
    try:
        parsed = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        errors.append("manifest created_at must use UTC format YYYY-MM-DDTHH:MM:SSZ")
    else:
        if parsed.strftime("%Y%m%d-%H%M%S") != timestamp:
            errors.append("manifest created_at and patch_timestamp disagree")
    if not 2 <= len(title.split()) <= 6 or len(title) > 80:
        errors.append("manifest title must contain 2-6 words and at most 80 characters")
    if not description or len(description) > 240 or description[-1:] not in ".!?":
        errors.append("manifest description must be one short sentence ending in punctuation")


def indexed_ids(value: object, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not value:
        errors.append(f"{label} must be a non-empty array")
        return []
    ids: list[str] = []
    for index, item in enumerate(value, 1):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            errors.append(f"{label}[{index}] must contain a non-empty id")
            continue
        ids.append(item["id"])
    if len(ids) != len(set(ids)):
        errors.append(f"{label} contains duplicate IDs")
    return ids


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate-patch-pack.py PATCH_PACK", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")

    manifest: dict[str, object] = {}
    manifest_path = root / "manifest.json"
    if manifest_path.is_file():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("root must be an object")
            manifest = loaded
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"invalid manifest JSON: {exc}")
        else:
            required_keys = {
                "schema_version", "patch_id", "title", "description", "created_at",
                "patch_timestamp", "patch_slug", "baseline_release", "evidence_directory",
                "workflow", "target", "files_created", "files_modified", "files_deleted",
                "requirements", "gates", "gpt_static_checks_performed",
                "gpt_runtime_checks_not_performed", "known_integration_risks",
                "forbidden_deviations",
            }
            missing = sorted(required_keys - manifest.keys())
            if missing:
                errors.append("manifest missing keys: " + ", ".join(missing))
            validate_identity(manifest, errors)
            workflow = manifest.get("workflow")
            target = manifest.get("target")
            if not isinstance(workflow, dict) or not SHA_RE.fullmatch(str(workflow.get("commit", ""))):
                errors.append("workflow.commit must be a real 40-character Git SHA")
            if not isinstance(target, dict) or not SHA_RE.fullmatch(str(target.get("base_revision", ""))):
                errors.append("target.base_revision must be a real 40-character Git SHA")

    requirement_ids = indexed_ids(manifest.get("requirements"), "manifest.requirements", errors) if manifest else []
    gate_ids = indexed_ids(manifest.get("gates"), "manifest.gates", errors) if manifest else []

    evidence_path = root / "evidence.json"
    if evidence_path.is_file():
        try:
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            if not isinstance(evidence, dict):
                raise ValueError("root must be an object")
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"invalid evidence JSON: {exc}")
        else:
            if evidence.get("schema_version") != 1:
                errors.append("evidence schema_version must be 1")
            implementation = evidence.get("implementation_commit")
            if implementation != "REPLACE_IMPLEMENTATION_COMMIT" and not SHA_RE.fullmatch(str(implementation)):
                errors.append("evidence implementation_commit must be the placeholder or a real SHA")
            evidence_req_ids = indexed_ids(evidence.get("requirements"), "evidence.requirements", errors)
            evidence_gate_ids = indexed_ids(evidence.get("gates"), "evidence.gates", errors)
            if set(evidence_req_ids) != set(requirement_ids):
                errors.append("evidence requirement IDs must exactly match manifest requirements")
            if set(evidence_gate_ids) != set(gate_ids):
                errors.append("evidence gate IDs must exactly match manifest gates")
            for item in evidence.get("requirements", []):
                if isinstance(item, dict) and item.get("status") != "pending":
                    errors.append("pre-execution evidence requirement status must be pending")
            for item in evidence.get("gates", []):
                if isinstance(item, dict) and item.get("status") != "pending":
                    errors.append("pre-execution evidence gate status must be pending")
            if evidence.get("deviations") != []:
                errors.append("pre-execution evidence deviations must be empty")
            if "evidence_commit" in evidence:
                errors.append("evidence.json must not contain evidence_commit")

    placeholders: list[str] = []
    allowed_placeholder_files = {"evidence.json"}
    for path in root.rglob("*"):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(root).as_posix()
        if "REPLACE" in text and relative not in allowed_placeholder_files:
            placeholders.append(relative)
    if placeholders:
        errors.append("unresolved REPLACE placeholders: " + ", ".join(sorted(placeholders)))

    scope_validator = Path(__file__).with_name("patch_pack_scope.py")
    if scope_validator.is_file():
        spec = importlib.util.spec_from_file_location("patch_pack_scope", scope_validator)
        if spec is None or spec.loader is None:
            errors.append("could not load patch_pack_scope.py")
        else:
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            errors.extend(module.validate_pack(root))
    else:
        errors.append("missing validator helper: scripts/patch_pack_scope.py")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
