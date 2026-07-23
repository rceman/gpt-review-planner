#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED_FILES = (
    "README_FIRST.md",
    "AGENT_PROMPT.md",
    "PATCH_SPEC.md",
    "BEHAVIOR_CONTRACT.md",
    "VALIDATION_REPORT.md",
    "manifest.json",
    "DEVIATIONS.md",
    "scripts/patch_pack_scope.py",
    "expected/acceptance-gates.md",
    "expected/allowed-deviations.md",
)

REQUIRED_VALIDATION_SECTIONS = (
    "GPT_STATIC_CHECKS_PERFORMED",
    "GPT_RUNTIME_CHECKS_NOT_PERFORMED",
    "AGENT_RUNTIME_GATES_REQUIRED",
    "AGENT_RUNTIME_RESULTS",
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate-patch-pack.py PATCH_PACK", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")

    manifest_path = root / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid manifest JSON: {exc}")
        else:
            required_keys = {
                "patch_id",
                "workflow",
                "target",
                "files_created",
                "files_modified",
                "files_deleted",
                "gpt_static_checks_performed",
                "gpt_runtime_checks_not_performed",
                "agent_runtime_gates_required",
                "agent_runtime_results",
                "known_integration_risks",
                "forbidden_deviations",
                "required_quality_gates",
            }
            missing = sorted(required_keys - manifest.keys())
            if missing:
                errors.append(f"manifest missing keys: {', '.join(missing)}")
            commit = str(manifest.get("workflow", {}).get("commit", ""))
            if commit.startswith("REPLACE_") or not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
                errors.append("workflow.commit must be a real 40-character Git SHA")

            runtime_results = manifest.get("agent_runtime_results")
            if not isinstance(runtime_results, str) or not runtime_results.strip():
                errors.append("manifest agent_runtime_results must be a non-empty string")

    report_path = root / "VALIDATION_REPORT.md"
    if report_path.is_file():
        report = report_path.read_text(encoding="utf-8")
        for section in REQUIRED_VALIDATION_SECTIONS:
            if section not in report:
                errors.append(f"VALIDATION_REPORT.md missing section: {section}")
        if "Pending local-agent execution." not in report:
            errors.append(
                "VALIDATION_REPORT.md must initially state: Pending local-agent execution."
            )

    placeholders: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name == ".gitkeep":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "REPLACE" in text:
            placeholders.append(str(path.relative_to(root)))

    if placeholders:
        errors.append("unresolved REPLACE placeholders: " + ", ".join(sorted(placeholders)))

    scope_validator = Path(__file__).with_name("patch_pack_scope.py")
    if scope_validator.is_file():
        import importlib.util

        spec = importlib.util.spec_from_file_location("patch_pack_scope", scope_validator)
        if spec is None or spec.loader is None:
            errors.append("could not load patch_pack_scope.py")
        else:
            module = importlib.util.module_from_spec(spec)
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
