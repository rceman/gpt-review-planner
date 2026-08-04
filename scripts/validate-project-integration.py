#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path
from pathlib import PurePosixPath

BEGIN = "<!-- BEGIN GPT-REVIEW-PLANNER -->"
END = "<!-- END GPT-REVIEW-PLANNER -->"


def _publication_validator():
    path = Path(__file__).with_name("validate-release-publication.py")
    spec = importlib.util.spec_from_file_location("project_release_publication_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("publication validator is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    project_ci = project / "scripts" / "check-github-ci.py"
    project_publication_validator = project / "scripts" / "validate-release-publication.py"
    project_publication_verifier = project / "scripts" / "verify-release-publication.py"
    publication_declaration = project / "release-publication.json"
    release_config = project / "release-config.json"
    planner_release = Path(__file__).resolve().with_name("release.py")
    conformance = Path(__file__).resolve().with_name("validate-release-tool-conformance.py")
    publication_mode: str | None = None
    if publication_declaration.is_symlink() or not publication_declaration.is_file():
        errors.append("missing or non-regular release-publication.json")
    else:
        try:
            publication = _publication_validator().load_publication_declaration(
                publication_declaration, repo_root=project
            )
            publication_mode = publication["mode"]
        except (OSError, UnicodeError, ValueError, RuntimeError):
            errors.append("invalid release-publication declaration")

    release_surfaces = {
        "scripts/release.py": project_release,
        "scripts/check-github-ci.py": project_ci,
        "scripts/validate-release-publication.py": project_publication_validator,
        "scripts/verify-release-publication.py": project_publication_verifier,
    }
    if publication_mode == "none":
        if release_config.exists() or release_config.is_symlink():
            errors.append("publication mode none must not include release-config.json")
        for label, path in release_surfaces.items():
            if path.exists() or path.is_symlink():
                errors.append(f"publication mode none must not include {label}")
    elif publication_mode in {"tag_only", "github_actions"}:
        if release_config.is_symlink() or not release_config.is_file():
            errors.append("active publication project must declare a regular release-config.json")
        missing_surfaces = [label for label, path in release_surfaces.items() if path.is_symlink() or not path.is_file()]
        for label in missing_surfaces:
            errors.append(f"active publication project must provide regular {label}")
        if not missing_surfaces and release_config.is_file() and not release_config.is_symlink():
            result = subprocess.run(
                [
                    sys.executable,
                    str(conformance),
                    "--release-script",
                    str(project_release),
                    "--ci-script",
                    str(project_ci),
                    "--canonical-script",
                    str(planner_release),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode != 0:
                errors.append("project release tooling failed planner conformance")

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
