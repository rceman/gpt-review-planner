#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import argparse
import subprocess
import sys
from pathlib import Path
from pathlib import PurePosixPath

BEGIN = "<!-- BEGIN GPT-REVIEW-PLANNER -->"
END = "<!-- END GPT-REVIEW-PLANNER -->"


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate lock key: {key}")
        result[key] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--agents-file", default="AGENTS.md")
    args = parser.parse_args()

    raw_agents = args.agents_file
    agents_relative = PurePosixPath(raw_agents)
    if (
        not raw_agents
        or "\\" in raw_agents
        or agents_relative.is_absolute()
        or "." in agents_relative.parts
        or ".." in agents_relative.parts
    ):
        parser.error("--agents-file must be a normalized project-relative path")

    project = Path(args.project).resolve()
    agents = project.joinpath(*agents_relative.parts)
    lock = project / ".gpt-workflow.lock"
    errors: list[str] = []

    project_release = project / "scripts" / "release.py"
    planner_release = Path(__file__).resolve().with_name("release.py")
    conformance = Path(__file__).resolve().with_name("validate-release-tool-conformance.py")
    if project_release.exists() or project_release.is_symlink():
        if project_release.is_symlink() or not project_release.is_file():
            errors.append("project scripts/release.py must be a regular file")
        else:
            result = subprocess.run(
                [
                    sys.executable,
                    str(conformance),
                    "--release-script",
                    str(project_release),
                    "--canonical-script",
                    str(planner_release),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode != 0:
                errors.append("project release tooling failed planner conformance: " + (result.stderr.strip() or "unknown error"))

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
            data = json.loads(lock.read_text(encoding="utf-8"), object_pairs_hook=lambda pairs: _unique_pairs(pairs))
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"invalid lock JSON: {exc}")
        else:
            required = {
                "schema_version",
                "repository",
                "version",
                "commit",
                "document",
                "installed_at",
                "execution_mode",
            }
            missing = sorted(required - data.keys())
            if missing:
                errors.append(f"lock missing keys: {', '.join(missing)}")
            unknown = sorted(set(data) - required)
            if unknown:
                errors.append(f"lock has unknown keys: {', '.join(unknown)}")
            if data.get("schema_version") != 2:
                errors.append("schema_version must be 2")
            if data.get("document") != "GPT_REVIEW_PLANNER.md":
                errors.append("document must be GPT_REVIEW_PLANNER.md")
            if not re.fullmatch(r"[0-9a-fA-F]{40}", str(data.get("commit", ""))):
                errors.append("commit must be a 40-character Git SHA")
            if data.get("execution_mode") not in {"gpt_tunnel_managed", "repository_evidence"}:
                errors.append("execution_mode must be explicitly gpt_tunnel_managed or repository_evidence")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"PASS: {project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
