#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BEGIN = "<!-- BEGIN GPT-REVIEW-PLANNER -->"
END = "<!-- END GPT-REVIEW-PLANNER -->"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate-project-integration.py PROJECT", file=sys.stderr)
        return 2

    project = Path(sys.argv[1]).resolve()
    agents = project / "AGENTS.md"
    lock = project / ".gpt-workflow.lock"
    errors: list[str] = []

    if not agents.is_file():
        errors.append("missing AGENTS.md")
    else:
        text = agents.read_text(encoding="utf-8")
        if text.count(BEGIN) != 1 or text.count(END) != 1:
            errors.append("AGENTS.md must contain exactly one managed workflow block")
        if not text.startswith(BEGIN):
            errors.append("managed workflow block must be at the beginning of AGENTS.md")

    if not lock.is_file():
        errors.append("missing .gpt-workflow.lock")
    else:
        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid lock JSON: {exc}")
        else:
            required = {
                "schema_version",
                "repository",
                "version",
                "commit",
                "document",
                "installed_at",
            }
            missing = sorted(required - data.keys())
            if missing:
                errors.append(f"lock missing keys: {', '.join(missing)}")
            if data.get("schema_version") != 1:
                errors.append("schema_version must be 1")
            if data.get("document") != "GPT_REVIEW_PLANNER.md":
                errors.append("document must be GPT_REVIEW_PLANNER.md")
            if not re.fullmatch(r"[0-9a-fA-F]{40}", str(data.get("commit", ""))):
                errors.append("commit must be a 40-character Git SHA")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"PASS: {project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
