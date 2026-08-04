#!/usr/bin/env python3
"""Verify declared tag CI/publication effects using read-only GitHub REST calls."""
from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "gpt_review_planner_release_publication_validator",
    Path(__file__).with_name("validate-release-publication.py"),
)
if _VALIDATOR_SPEC is None or _VALIDATOR_SPEC.loader is None:
    raise RuntimeError("cannot load the canonical publication validator")
_VALIDATOR = importlib.util.module_from_spec(_VALIDATOR_SPEC)
_VALIDATOR_SPEC.loader.exec_module(_VALIDATOR)
PublicationError = _VALIDATOR.PublicationError
load_publication_declaration = _VALIDATOR.load_publication_declaration
tag_matches = _VALIDATOR.tag_matches


SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PublicationError("created-after must be RFC3339") from exc
    if parsed.tzinfo is None:
        raise PublicationError("created-after must include a timezone")
    return parsed.astimezone(timezone.utc)


def fetch(url: str, token: str | None) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "User-Agent": "gpt-review-planner-release-publication-check",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def output(args: argparse.Namespace, state: str, message: str, **values: object) -> dict[str, object]:
    source = values.pop(
        "source",
        "github-actions-rest" if state not in {"not_applicable", "invalid_response"} else "policy",
    )
    data: dict[str, object] = {
        "schema_version": 1,
        "repository": args.repository,
        "tag": args.tag,
        "mode": values.pop("mode", None),
        "state": state,
        "blocking": state not in {"success", "not_applicable"},
        "source": source,
        "run_id": None,
        "job_id": None,
        "run_url": None,
        "job_url": None,
        "checked_sha": None,
        "conclusion": None,
        "created_at": None,
        "release_id": None,
        "release_state": None,
        "asset_state": None,
        "asset_names": [],
        "message": message,
    }
    data.update(values)
    if args.format == "json":
        print(json.dumps(data, sort_keys=True))
    else:
        print(f"{state}: {message}")
    return data


def resolve_tag(repo: Path, tag: str) -> tuple[str, bool]:
    import subprocess
    check = subprocess.run(["git", "cat-file", "-t", f"refs/tags/{tag}"], cwd=repo, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if check.returncode != 0 or check.stdout.strip() != "tag":
        raise PublicationError("tag must exist as an annotated tag")
    commit = subprocess.run(["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"], cwd=repo, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    sha = commit.stdout.strip()
    if commit.returncode != 0 or not SHA_RE.fullmatch(sha):
        raise PublicationError("tag does not resolve to a canonical commit")
    return sha, True


def pick_run(payload: object, args: argparse.Namespace, declaration: dict[str, object], sha: str) -> dict[str, object]:
    if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
        raise PublicationError("workflow response has invalid workflow_runs")
    workflow = declaration["workflow"]
    assert isinstance(workflow, dict)
    candidates: list[dict[str, object]] = []
    for item in payload["workflow_runs"]:
        if not isinstance(item, dict):
            continue
        if item.get("head_sha") != sha or item.get("event") != "push":
            continue
        if item.get("name") != workflow["name"] or item.get("path") != workflow["path"]:
            continue
        if item.get("head_branch") != args.tag:
            continue
        if args.created_after_time:
            created_at = item.get("created_at")
            if not isinstance(created_at, str) or parse_timestamp(created_at) <= args.created_after_time:
                continue
        if str(item.get("id")) in args.exclude_run_id:
            continue
        candidates.append(item)
    if not candidates:
        raise PublicationError("no distinct matching tag workflow run was found")
    return sorted(candidates, key=lambda item: (str(item.get("created_at", "")), int(item.get("id", 0) or 0)), reverse=True)[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--declaration", type=Path)
    parser.add_argument("--repository", default="")
    parser.add_argument("--tag")
    parser.add_argument("--api-url", default="https://api.github.com")
    parser.add_argument("--created-after")
    parser.add_argument("--exclude-run-id", action="append", default=[])
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    args.repository = args.repository or "local/repository"
    declaration_path = args.declaration or (args.repo / "release-publication.json")
    mode: str | None = None
    report_values: dict[str, object] = {}
    try:
        declaration = load_publication_declaration(declaration_path, repo_root=args.repo)
        if any(not re.fullmatch(r"[0-9]+", value) for value in args.exclude_run_id):
            raise PublicationError("excluded run IDs must be decimal integers")
        mode = declaration["mode"]
        if mode == "none":
            output(
                args,
                "not_applicable",
                "publication is disabled by repository declaration",
                mode=mode,
                release_state="not_applicable",
                asset_state="not_applicable",
            )
            return 0
        if not args.tag:
            raise PublicationError("--tag is required for active publication modes")
        tag_declaration = declaration["tag"]
        assert isinstance(tag_declaration, dict)
        if not tag_matches(str(tag_declaration["pattern"]), args.tag):
            raise PublicationError("tag does not match the declared release tag pattern")
        sha, _ = resolve_tag(args.repo, args.tag)
        if mode == "tag_only" and declaration["workflow"] is None:
            output(
                args,
                "success",
                "annotated tag verified; no post-tag workflow is declared",
                mode=mode,
                source="policy",
                checked_sha=sha,
                release_state="not_applicable",
                asset_state="not_applicable",
            )
            return 0
        if not args.created_after:
            raise PublicationError("--created-after is required for active workflow publication modes")
        args.created_after_time = parse_timestamp(args.created_after)
        if not REPOSITORY_RE.fullmatch(args.repository):
            raise PublicationError("--repository OWNER/REPO is required for active publication modes")
        workflow = declaration["workflow"]
        assert isinstance(workflow, dict)
        base = args.api_url.rstrip("/")
        payload = fetch(f"{base}/repos/{args.repository}/actions/runs?event=push&per_page=100", None)
        run = pick_run(payload, args, declaration, sha)
        run_id = run.get("id")
        if not isinstance(run_id, int):
            raise PublicationError("selected workflow run has no numeric id")
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            output(args, "failed", "distinct tag workflow did not complete successfully", mode=mode,
                   run_id=run_id, run_url=run.get("html_url"), checked_sha=run.get("head_sha"),
                   conclusion=run.get("conclusion"), created_at=run.get("created_at"))
            return 3
        jobs = fetch(f"{base}/repos/{args.repository}/actions/runs/{run_id}/jobs?per_page=100", None)
        if not isinstance(jobs, dict) or not isinstance(jobs.get("jobs"), list):
            raise PublicationError("jobs response has invalid shape")
        job = next((item for item in jobs["jobs"] if isinstance(item, dict)), None)
        if not isinstance(job, dict):
            raise PublicationError("selected workflow run has no job metadata")
        expected_assets = declaration["assets"]
        assert isinstance(expected_assets, dict)
        values: dict[str, object] = {
            "mode": mode, "run_id": run_id, "job_id": job.get("id"),
            "run_url": run.get("html_url"), "job_url": job.get("html_url"),
            "checked_sha": run.get("head_sha"), "conclusion": run.get("conclusion"),
            "created_at": run.get("created_at"),
            "release_state": "not_applicable" if mode == "tag_only" else None,
            "asset_state": "not_run" if mode == "github_actions" and expected_assets["expected"] else "not_applicable",
        }
        if mode == "github_actions":
            report_values = dict(values)
            report_values["release_state"] = "unavailable"
            release = fetch(f"{base}/repos/{args.repository}/releases/tags/{args.tag}", None)
            if not isinstance(release, dict) or release.get("tag_name") != args.tag:
                values["release_state"] = "failed"
                report_values = dict(values)
                output(args, "failed", "GitHub Release metadata does not match the tag", **values)
                return 3
            if not isinstance(release.get("id"), int):
                values["release_state"] = "failed"
                report_values = dict(values)
                output(args, "failed", "GitHub Release metadata has no numeric id", **values)
                return 3
            expected_release = declaration["github_release"]
            assert isinstance(expected_release, dict)
            for field in ("draft", "prerelease"):
                if release.get(field) != expected_release[field]:
                    values["release_state"] = "failed"
                    report_values = dict(values)
                    output(args, "failed", f"GitHub Release {field} does not match declaration", **values)
                    return 3
            values.update(release_id=release.get("id"), release_state="success")
            report_values = dict(values)
            if expected_assets["expected"]:
                values["asset_state"] = "unavailable"
                report_values = dict(values)
                assets_payload = fetch(
                    f"{base}/repos/{args.repository}/releases/{release.get('id')}/assets?per_page=100",
                    None,
                )
                if not isinstance(assets_payload, list):
                    raise PublicationError("release assets response has invalid shape")
                names = [
                    item.get("name")
                    for item in assets_payload
                    if isinstance(item, dict) and isinstance(item.get("name"), str)
                ]
                patterns = expected_assets["published_name_patterns"]
                if not all(any(fnmatch.fnmatch(name, pattern) for name in names) for pattern in patterns):
                    values.update(asset_state="failed", asset_names=names)
                    output(args, "failed", "declared release assets are missing", **values)
                    return 3
                values.update(asset_state="success", asset_names=names)
            else:
                values.update(asset_state="not_applicable", asset_names=[])
        message = "declared release publication verified"
        if mode == "github_actions" and values.get("asset_state") == "not_applicable":
            message = "declared GitHub Release metadata verified; asset proof not applicable"
        output(args, "success", message, **values)
        return 0
    except HTTPError as exc:
        error_values = dict(report_values)
        error_values.setdefault("mode", mode)
        output(args, "unavailable", f"publication query returned HTTP {exc.code}", **error_values)
        return 4
    except (URLError, OSError, ValueError, json.JSONDecodeError, PublicationError) as exc:
        error_values = dict(report_values)
        error_values.setdefault("mode", mode)
        output(args, "invalid_response", str(exc), **error_values)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
