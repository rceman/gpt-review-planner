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
    "expected/acceptance-gates.md",
    "expected/allowed-deviations.md",
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
                "locally_validated",
                "requires_agent_validation",
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

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"PASS: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
