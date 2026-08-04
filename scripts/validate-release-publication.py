#!/usr/bin/env python3
"""Validate a repository's strict release-publication declaration.

This module is intentionally dependency-free.  Other planner validators import
``load_publication_declaration`` instead of maintaining a second contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


MODES = {"none", "tag_only", "github_actions"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TAG_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")
WORKFLOW_PATH_RE = re.compile(r"^\.github/workflows/[^/]+\.(?:yml|yaml)$")
SAFE_PART_RE = re.compile(r"^[^/\\]+$")
MAX_WORKFLOW_BYTES = 512 * 1024
MAX_WORKFLOW_LINES = 10_000


class PublicationError(ValueError):
    """Raised when a publication declaration or workflow is invalid."""


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PublicationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PublicationError(f"cannot read {path}: {exc}") from exc
    try:
        return json.loads(raw, object_pairs_hook=_no_duplicate_pairs)
    except json.JSONDecodeError as exc:
        raise PublicationError(f"invalid JSON in {path}: {exc.msg}") from exc


def _object(value: Any, label: str, keys: set[str], required: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PublicationError(f"{label} must be an object")
    unknown = set(value) - keys
    missing = required - set(value)
    if unknown:
        raise PublicationError(f"{label} contains unknown field(s): {', '.join(sorted(unknown))}")
    if missing:
        raise PublicationError(f"{label} is missing field(s): {', '.join(sorted(missing))}")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PublicationError(f"{label} must be a non-empty string")
    return value


def _bool(value: Any, label: str, expected: bool | None = None) -> bool:
    if not isinstance(value, bool):
        raise PublicationError(f"{label} must be boolean")
    if expected is not None and value is not expected:
        raise PublicationError(f"{label} must be {str(expected).lower()}")
    return value


def _string_list(value: Any, label: str, *, non_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (non_empty and not value):
        raise PublicationError(f"{label} must be an {'non-empty ' if non_empty else ''}array of strings")
    if any(not isinstance(item, str) or not item for item in value):
        raise PublicationError(f"{label} must contain only non-empty strings")
    return value


def validate_workflow_path(path: str) -> None:
    if (
        not WORKFLOW_PATH_RE.fullmatch(path)
        or ".." in path.split("/")
        or any(not SAFE_PART_RE.fullmatch(part) for part in path.split("/"))
    ):
        raise PublicationError(f"workflow.path is not a normalized repository-relative workflow path: {path!r}")


def _validate_none(data: dict[str, Any]) -> dict[str, Any]:
    _object(data, "publication declaration", {"schema_version", "mode"}, {"schema_version", "mode"})
    if data["schema_version"] != 1 or isinstance(data["schema_version"], bool):
        raise PublicationError("schema_version must be integer 1")
    if data["mode"] != "none":
        raise PublicationError("none declaration has invalid mode")
    return data


def _validate_active(data: dict[str, Any]) -> dict[str, Any]:
    top_keys = {
        "schema_version", "mode", "tag", "workflow", "credential_authority",
        "local_credentials_required", "tag_push_side_effects", "github_release",
        "assets", "proof_requirements",
    }
    _object(data, "publication declaration", top_keys, top_keys)
    if data["schema_version"] != 1 or isinstance(data["schema_version"], bool):
        raise PublicationError("schema_version must be integer 1")
    mode = data["mode"]
    if mode not in {"tag_only", "github_actions"}:
        raise PublicationError("active declaration mode must be tag_only or github_actions")

    tag = _object(data["tag"], "tag", {"pattern", "annotated", "push_required", "identity_source"},
                  {"pattern", "annotated", "push_required", "identity_source"})
    pattern = _string(tag["pattern"], "tag.pattern")
    if not TAG_RE.fullmatch(pattern.replace("\\.", ".")) and pattern not in {"v*", "vX.Y.Z"}:
        raise PublicationError("tag.pattern must describe a vX.Y.Z release tag")
    _bool(tag["annotated"], "tag.annotated", True)
    _bool(tag["push_required"], "tag.push_required", True)
    if tag["identity_source"] != "release-config.json":
        raise PublicationError("tag.identity_source must be release-config.json")

    expected_purpose = "tag_validation" if mode == "tag_only" else "release_publication"
    workflow = data["workflow"]
    if workflow is not None:
        workflow = _object(
            workflow,
            "workflow",
            {"path", "name", "sha256", "purpose", "event", "tag_trigger", "tag_patterns",
             "permissions", "distinct_run_required", "created_after_tag_push"},
            {"path", "name", "sha256", "purpose", "event", "tag_trigger", "tag_patterns",
             "permissions", "distinct_run_required", "created_after_tag_push"},
        )
        workflow_path = _string(workflow["path"], "workflow.path")
        validate_workflow_path(workflow_path)
        _string(workflow["name"], "workflow.name")
        workflow_sha = _string(workflow["sha256"], "workflow.sha256")
        if not SHA256_RE.fullmatch(workflow_sha):
            raise PublicationError("workflow.sha256 must be 64 lowercase hexadecimal characters")
        if workflow["purpose"] != expected_purpose:
            raise PublicationError(f"workflow.purpose must be {expected_purpose!r} for mode {mode!r}")
        if workflow["event"] != "push":
            raise PublicationError("workflow.event must be push")
        trigger = workflow["tag_trigger"]
        if trigger not in {"explicit_tags_filter", "unfiltered_push"}:
            raise PublicationError("workflow.tag_trigger must be explicit_tags_filter or unfiltered_push")
        patterns = _string_list(workflow["tag_patterns"], "workflow.tag_patterns", non_empty=trigger == "explicit_tags_filter")
        if trigger == "unfiltered_push" and patterns:
            raise PublicationError("unfiltered workflow.tag_patterns must be empty")
        permissions = _object(workflow["permissions"], "workflow.permissions", {"contents"}, {"contents"})
        expected_permission = "read" if mode == "tag_only" else "write"
        if permissions["contents"] != expected_permission:
            raise PublicationError(f"workflow.permissions.contents must be {expected_permission!r}")
        _bool(workflow["distinct_run_required"], "workflow.distinct_run_required", True)
        _bool(workflow["created_after_tag_push"], "workflow.created_after_tag_push", True)
    elif mode != "tag_only":
        raise PublicationError("github_actions requires an explicit workflow object")

    authority = data["credential_authority"]
    expected_authority = "none" if mode == "tag_only" else "github.token"
    if authority != expected_authority:
        raise PublicationError(f"credential_authority must be {expected_authority!r}")
    _bool(data["local_credentials_required"], "local_credentials_required", False)
    effects = _string_list(data["tag_push_side_effects"], "tag_push_side_effects")
    if any(effect not in {"tag_ci", "github_release_create_or_update", "asset_upload"} for effect in effects):
        raise PublicationError("tag_push_side_effects contains an unsupported automatic effect")

    release = _object(data["github_release"], "github_release", {"behavior", "expected", "draft", "prerelease", "notes"},
                      {"behavior", "expected", "draft", "prerelease", "notes"})
    assets = _object(
        data["assets"], "assets",
        {"policy", "expected", "workflow_source_patterns", "published_name_patterns"},
        {"policy", "expected", "workflow_source_patterns", "published_name_patterns"},
    )
    policy = assets["policy"]
    if policy not in {"none", "workflow_produced"}:
        raise PublicationError("assets.policy is invalid")
    release_expected = _bool(release["expected"], "github_release.expected")
    behavior = release["behavior"]
    if behavior not in {"none", "create_or_update"}:
        raise PublicationError("github_release.behavior is invalid")
    if (behavior == "create_or_update") != release_expected:
        raise PublicationError("github_release.behavior and expected must agree")
    _bool(release["draft"], "github_release.draft")
    _bool(release["prerelease"], "github_release.prerelease")
    notes = _object(release["notes"], "github_release.notes", {"source", "file"}, {"source"})
    notes_source = notes["source"]
    if notes_source not in {"none", "generated", "changelog", "declared_file"}:
        raise PublicationError("github_release.notes.source is invalid")
    if notes_source == "declared_file":
        if set(notes) != {"source", "file"}:
            raise PublicationError("declared_file notes require exactly one file")
        note_file = _string(notes["file"], "github_release.notes.file")
        if note_file.startswith(("/", "\\")) or ".." in note_file.split("/") or "\\" in note_file:
            raise PublicationError("github_release.notes.file must be repository-relative")
    elif set(notes) != {"source"}:
        raise PublicationError("github_release.notes.file is permitted only for declared_file")
    asset_expected = _bool(assets["expected"], "assets.expected")
    if (policy == "workflow_produced") != asset_expected:
        raise PublicationError("assets.policy and expected must agree")
    source_patterns = _string_list(assets["workflow_source_patterns"], "assets.workflow_source_patterns", non_empty=asset_expected)
    published_patterns = _string_list(assets["published_name_patterns"], "assets.published_name_patterns", non_empty=asset_expected)
    if not asset_expected and (source_patterns or published_patterns):
        raise PublicationError("asset patterns must be empty when assets are not expected")
    expected_effects = [] if workflow is None else ["tag_ci"]
    if release_expected:
        expected_effects.append("github_release_create_or_update")
    if asset_expected:
        expected_effects.append("asset_upload")
    if effects != expected_effects:
        raise PublicationError("tag_push_side_effects does not match declared automatic effects")
    if mode == "tag_only" and (release_expected or behavior != "none" or asset_expected or notes_source != "none"):
        raise PublicationError("tag_only cannot declare GitHub release or asset publication")
    if mode == "github_actions" and not release_expected:
        raise PublicationError("github_actions must declare an expected GitHub Release")
    proofs = _object(
        data["proof_requirements"],
        "proof_requirements",
        {"tag_ci", "distinct_post_tag_workflow", "release_metadata", "assets"},
        {"tag_ci", "distinct_post_tag_workflow", "release_metadata", "assets"},
    )
    _bool(proofs["tag_ci"], "proof_requirements.tag_ci", workflow is not None)
    _bool(proofs["distinct_post_tag_workflow"], "proof_requirements.distinct_post_tag_workflow", workflow is not None)
    _bool(proofs["release_metadata"], "proof_requirements.release_metadata", release_expected)
    _bool(proofs["assets"], "proof_requirements.assets", asset_expected)
    return data


def validate_declaration(data: Any, *, repo_root: Path | None = None) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise PublicationError("publication declaration must be an object")
    mode = data.get("mode")
    if mode not in MODES:
        raise PublicationError("mode must be exactly one of none, tag_only, github_actions")
    normalized = _validate_none(data) if mode == "none" else _validate_active(data)
    if repo_root is not None and mode != "none":
        workflow = normalized["workflow"]
        assets = normalized["assets"]
        if workflow is None:
            return normalized
        assert isinstance(workflow, dict) and isinstance(assets, dict)
        source_patterns = assets["workflow_source_patterns"]
        path = (repo_root / workflow["path"]).resolve()
        root = repo_root.resolve()
        if root not in path.parents:
            raise PublicationError("workflow.path escapes the repository")
        try:
            scan = scan_workflow(path)
        except (OSError, UnicodeError) as exc:
            raise PublicationError(f"cannot inspect declared workflow: {exc}") from exc
        if scan["sha256"] != workflow["sha256"]:
            raise PublicationError("workflow.sha256 does not match the declared workflow")
        if scan["name"] != workflow["name"]:
            raise PublicationError("workflow.name does not match the declared workflow")
        if scan["event"] != workflow["event"]:
            raise PublicationError("workflow.event does not match the declared workflow")
        if scan["tag_trigger"] != workflow["tag_trigger"]:
            raise PublicationError("workflow.tag_trigger does not match the declared workflow")
        if scan["tag_patterns"] != workflow["tag_patterns"]:
            raise PublicationError("workflow.tag_patterns do not match the declared workflow")
        if scan["contents_permission"] != workflow["permissions"]["contents"]:
            raise PublicationError("workflow permissions do not match the declared workflow")
        if scan["release_source_patterns"] != source_patterns:
            raise PublicationError("assets.workflow_source_patterns do not match the declared workflow")
        if normalized["mode"] == "github_actions" and not scan["github_release"]:
            raise PublicationError("declared GitHub publication workflow has no release operation")
        if normalized["mode"] == "tag_only" and scan["github_release"]:
            raise PublicationError("tag_only workflow must not publish a GitHub Release")
    return normalized


def scan_workflow(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_WORKFLOW_BYTES:
        raise PublicationError("workflow exceeds bounded scan size")
    text = raw.decode("utf-8")
    lines = text.splitlines()
    if len(lines) > MAX_WORKFLOW_LINES:
        raise PublicationError("workflow exceeds bounded scan line count")
    name: str | None = None
    event = "push" if re.search(r"(?m)^\s*push\s*:", text) else None
    explicit_patterns: list[str] = []
    push_line = None
    on_line = None
    for index, line in enumerate(lines):
        if re.match(r"^name\s*:", line):
            name = line.split(":", 1)[1].strip().strip("\"'")
        if re.match(r"^on\s*:\s*$", line):
            on_line = index
        if on_line is not None and re.match(r"^\s{2}push\s*:", line):
            push_line = index
        if push_line is not None and index >= push_line:
            if index > push_line and line and not line.startswith((" ", "\t")):
                break
            match = re.search(r"tags\s*:\s*\[([^]]*)\]", line)
            if match:
                explicit_patterns.extend(re.findall(r"['\"]([^'\"]+)['\"]", match.group(1)))
            elif re.match(r"^\s+tags\s*:\s*$", line):
                for following in lines[index + 1:]:
                    item = re.match(r"^\s+-\s+['\"]?([^'\"\s]+)['\"]?\s*$", following)
                    if item:
                        explicit_patterns.append(item.group(1))
                    elif following and not following.startswith((" ", "\t")):
                        break
    if name is None or event is None:
        raise PublicationError("workflow must declare a top-level name and push event")
    permissions = "none"
    for line in lines:
        match = re.match(r"^\s+contents\s*:\s*(read|write)\s*$", line)
        if match:
            permissions = match.group(1)
            break
    release_commands = re.findall(r"\bgh\s+release\s+(?:create|upload)\b[^\n]*", text)
    has_release = bool(release_commands)
    if has_release and "GH_TOKEN: ${{ github.token }}" not in text and "GH_TOKEN:${{ github.token }}" not in text:
        raise PublicationError("GitHub publication workflow must use github.token")
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "name": name,
        "event": event,
        "tag_trigger": "explicit_tags_filter" if explicit_patterns else "unfiltered_push",
        "tag_patterns": explicit_patterns,
        "contents_permission": permissions,
        "github_release": has_release,
        "release_source_patterns": sorted(set(re.findall(r"(?:^|\s)(dist/\*|[^\s'\"]+/\*)", "\n".join(release_commands)))),
    }


def tag_matches(pattern: str, tag: str) -> bool:
    """Match a release tag against the declaration's tag pattern."""
    if pattern == "vX.Y.Z":
        return bool(re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag))
    if pattern == "v*":
        return bool(re.fullmatch(r"v[^/]+", tag))
    return pattern == tag


def load_publication_declaration(path: Path, *, repo_root: Path | None = None) -> dict[str, Any]:
    return validate_declaration(load_json(path), repo_root=repo_root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("declaration", type=Path)
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args(argv)
    try:
        data = load_publication_declaration(args.declaration, repo_root=args.repo)
    except PublicationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("PASS: " + json.dumps(data, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
