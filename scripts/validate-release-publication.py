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
import shlex
import sys
from pathlib import Path
from typing import Any


MODES = {"none", "tag_only", "github_actions"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TAG_RE = re.compile(r"^v(?:\*|X\.Y\.Z|[0-9]+\.[0-9]+\.[0-9]+)$")
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
    except UnicodeError as exc:
        raise PublicationError("cannot read publication declaration as UTF-8") from exc
    except OSError as exc:
        raise PublicationError("cannot read publication declaration") from exc
    try:
        return json.loads(raw, object_pairs_hook=_no_duplicate_pairs)
    except json.JSONDecodeError as exc:
        raise PublicationError(f"invalid publication declaration JSON: {exc.msg}") from exc


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
    if len(set(value)) != len(value):
        raise PublicationError(f"{label} must not contain duplicates")
    return value


def validate_workflow_path(path: str) -> None:
    if (
        not WORKFLOW_PATH_RE.fullmatch(path)
        or ".." in path.split("/")
        or any(not SAFE_PART_RE.fullmatch(part) for part in path.split("/"))
    ):
        raise PublicationError("workflow.path is not a normalized repository-relative workflow path")


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
    if not TAG_RE.fullmatch(pattern):
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
    if release_expected and notes_source == "none":
        raise PublicationError("an expected GitHub Release must declare a notes source")
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
            raise PublicationError("cannot inspect declared workflow") from exc
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
        if normalized["mode"] == "tag_only":
            if scan["github_release"]:
                raise PublicationError("tag_only workflow must not publish a GitHub Release")
        else:
            if not scan["canonical_release_topology"]:
                raise PublicationError("github_actions workflow must use the canonical release fallback")
            if not scan["release_view"] or not scan["release_create"]:
                raise PublicationError("github_actions workflow must ensure a release with view and create")
            if scan["credential_authority"] != "github.token":
                raise PublicationError("github_actions workflow must use github.token")
            release_notes = normalized["github_release"]["notes"]
            assert isinstance(release_notes, dict)
            if scan["notes_source"] != release_notes["source"]:
                raise PublicationError("workflow notes source does not match the declaration")
            if release_notes["source"] == "declared_file" and scan["notes_file"] != release_notes.get("file"):
                raise PublicationError("workflow notes file does not match the declaration")
            if scan["draft"] != normalized["github_release"]["draft"]:
                raise PublicationError("workflow draft flag does not match the declaration")
            if scan["prerelease"] != normalized["github_release"]["prerelease"]:
                raise PublicationError("workflow prerelease flag does not match the declaration")
            if assets["expected"]:
                if not scan["release_upload"] or not scan["upload_clobber"]:
                    raise PublicationError("workflow-produced assets require upload with --clobber")
            elif scan["release_upload"]:
                raise PublicationError("asset policy none forbids release uploads")
    return normalized


def _indent(line: str) -> int:
    if line.startswith("\t"):
        raise PublicationError("workflow uses unsupported tab indentation")
    return len(line) - len(line.lstrip(" "))


def _scalar_list(raw: str, label: str) -> list[str]:
    value = raw.strip()
    if not (value.startswith("[") and value.endswith("]")):
        raise PublicationError(f"workflow {label} uses unsupported list syntax")
    inner = value[1:-1].strip()
    if not inner:
        return []
    items = []
    for item in inner.split(","):
        item = item.strip()
        if len(item) >= 2 and item[0] == item[-1] and item[0] in "'\"":
            item = item[1:-1]
        if not item or any(char in item for char in "[]{}"):
            raise PublicationError(f"workflow {label} contains unsupported list data")
        items.append(item)
    if len(set(items)) != len(items):
        raise PublicationError(f"workflow {label} contains duplicate values")
    return items


def _run_blocks(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    for index, line in enumerate(lines):
        match = re.match(r"^( *)(?:run):(?:\s*)(.*)$", line)
        if not match:
            continue
        base = len(match.group(1))
        rest = match.group(2).strip()
        if rest and not rest.startswith(("|", ">")):
            blocks.append(rest)
            continue
        body: list[str] = []
        for following in lines[index + 1:]:
            if following.strip() and _indent(following) <= base:
                break
            body.append(following.strip())
        blocks.append("\n".join(body))
    return blocks


def _env_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^( *)env:\s*$", line)
        if not match:
            continue
        base = len(match.group(1))
        body: list[str] = []
        for following in lines[index + 1:]:
            if following.strip() and _indent(following) <= base:
                break
            body.append(following)
        blocks.append(body)
    return blocks


def _join_shell_continuations(lines: list[str]) -> list[str]:
    joined: list[str] = []
    pending = ""
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if any(operator in line for operator in (";", "&&", "||", "|")):
            raise PublicationError("workflow release branches use unsupported shell operators")
        if line.endswith("\\"):
            pending += line[:-1].rstrip() + " "
            continue
        joined.append((pending + line).strip())
        pending = ""
    if pending:
        raise PublicationError("workflow release branch has a truncated continuation")
    return joined


def _release_command_tokens(line: str, command: str) -> list[str]:
    try:
        tokens = shlex.split(line, posix=True)
    except ValueError as exc:
        raise PublicationError("workflow contains malformed release command syntax") from exc
    if len(tokens) < 4 or tokens[:3] != ["gh", "release", command] or tokens[3] != "$tag":
        raise PublicationError("workflow release branch does not use the canonical tag command")
    return tokens


def _canonical_release_topology(run_blocks: list[str]) -> dict[str, Any] | None:
    marker = re.compile(r'^if gh release view "\$tag" >/dev/null 2>&1; then$')
    candidates: list[tuple[list[str], int]] = []
    for block in run_blocks:
        lines = block.splitlines()
        for index, line in enumerate(lines):
            if marker.fullmatch(line.strip()):
                candidates.append((lines, index))
    if not candidates:
        return None
    if len(candidates) != 1:
        raise PublicationError("workflow must contain exactly one canonical release fallback")

    lines, if_index = candidates[0]
    else_indices = [index for index in range(if_index + 1, len(lines)) if lines[index].strip() == "else"]
    fi_indices = [index for index in range(if_index + 1, len(lines)) if lines[index].strip() == "fi"]
    if len(else_indices) != 1 or len(fi_indices) != 1 or else_indices[0] >= fi_indices[0]:
        raise PublicationError("workflow release fallback must contain one else and one fi")
    else_index, fi_index = else_indices[0], fi_indices[0]
    if any(line.strip().startswith("if ") for line in lines[if_index + 1:fi_index]):
        raise PublicationError("workflow release fallback must not contain nested conditionals")

    success_lines = _join_shell_continuations(lines[if_index + 1:else_index])
    fallback_lines = _join_shell_continuations(lines[else_index + 1:fi_index])
    upload_tokens: list[str] | None = None
    if len(success_lines) == 1 and success_lines[0] == ":":
        pass
    elif len(success_lines) == 1:
        upload_tokens = _release_command_tokens(success_lines[0], "upload")
        if "--clobber" not in upload_tokens:
            raise PublicationError("workflow existing-release branch must upload with --clobber")
    else:
        raise PublicationError("workflow existing-release branch must contain canonical upload or :")
    if len(fallback_lines) != 1:
        raise PublicationError("workflow fallback branch must contain one canonical create command")
    create_tokens = _release_command_tokens(fallback_lines[0], "create")
    return {"upload_tokens": upload_tokens, "create_tokens": create_tokens}


def scan_workflow(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise PublicationError("workflow is not valid UTF-8") from exc
    except OSError as exc:
        raise PublicationError("cannot read declared workflow") from exc
    if len(raw) > MAX_WORKFLOW_BYTES:
        raise PublicationError("workflow exceeds bounded scan size")
    lines = text.splitlines()
    if len(lines) > MAX_WORKFLOW_LINES:
        raise PublicationError("workflow exceeds bounded scan line count")

    top: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$", line)
        if match:
            top.append((index, match.group(1), (match.group(2) or "").strip()))

    def top_marker(key: str) -> tuple[int, str]:
        matches = [(index, rest) for index, name, rest in top if name == key]
        if len(matches) != 1:
            raise PublicationError(f"workflow must contain exactly one top-level {key} marker")
        return matches[0]

    name_index, name_value = top_marker("name")
    if not name_value:
        raise PublicationError("workflow top-level name must be non-empty")
    name = name_value.strip("\"'")
    on_index, on_value = top_marker("on")
    permissions_index, permissions_value = top_marker("permissions")
    if on_value or permissions_value:
        raise PublicationError("workflow on and permissions markers must use the supported block form")
    if any(name == "push" for _, name, _ in top):
        raise PublicationError("workflow contains an unsupported top-level push marker")

    def block_end(start: int) -> int:
        for index in range(start + 1, len(lines)):
            if lines[index].strip() and _indent(lines[index]) == 0:
                return index
        return len(lines)

    on_end = block_end(on_index)
    on_block = lines[on_index + 1:on_end]
    push_markers = []
    for relative, line in enumerate(on_block):
        if re.match(r"^\s*push\s*:", line):
            push_markers.append((relative, line))
    if len(push_markers) != 1 or _indent(push_markers[0][1]) != 2:
        raise PublicationError("workflow must contain exactly one supported on.push marker")
    push_relative, push_line = push_markers[0]
    if push_line.split(":", 1)[1].strip():
        raise PublicationError("workflow on.push must use the supported block form")
    push_index = on_index + 1 + push_relative
    push_end = on_end
    for index in range(push_index + 1, on_end):
        if lines[index].strip() and _indent(lines[index]) <= 2:
            push_end = index
            break
    tag_markers: list[tuple[int, str]] = []
    for index in range(push_index + 1, push_end):
        if re.search(r"\btags\s*:", lines[index]):
            if _indent(lines[index]) != 4:
                raise PublicationError("workflow tags marker is not anchored to on.push")
            tag_markers.append((index, lines[index]))
    if len(tag_markers) > 1:
        raise PublicationError("workflow contains duplicate on.push.tags markers")
    explicit_patterns: list[str] = []
    if tag_markers:
        tag_index, tag_line = tag_markers[0]
        tag_value = tag_line.split(":", 1)[1].strip()
        if tag_value:
            explicit_patterns = _scalar_list(tag_value, "on.push.tags")
        else:
            for following in lines[tag_index + 1:push_end]:
                if not following.strip():
                    continue
                if _indent(following) <= 4:
                    break
                item = re.match(r"^\s{6}-\s+(.+?)\s*$", following)
                if not item:
                    raise PublicationError("workflow on.push.tags uses unsupported list syntax")
                value = item.group(1).strip("\"'")
                if not value:
                    raise PublicationError("workflow on.push.tags contains an empty pattern")
                explicit_patterns.append(value)
            if len(set(explicit_patterns)) != len(explicit_patterns):
                raise PublicationError("workflow on.push.tags contains duplicate values")

    permission_end = block_end(permissions_index)
    content_markers: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        if re.search(r"\bcontents\s*:", line):
            content_markers.append((index, line))
    if len(content_markers) != 1 or not (permissions_index < content_markers[0][0] < permission_end):
        raise PublicationError("workflow must contain exactly one top-level permissions.contents marker")
    content_line = content_markers[0][1]
    if _indent(content_line) != 2:
        raise PublicationError("workflow permissions.contents marker is not top-level")
    permission_value = content_line.split(":", 1)[1].strip()
    if permission_value not in {"read", "write"}:
        raise PublicationError("workflow permissions.contents must be read or write")

    run_blocks = _run_blocks(lines)
    run_text = "\n".join(run_blocks)
    normalized_run = re.sub(r"\\\s*\n\s*", " ", run_text)
    commands: list[tuple[str, list[str]]] = []
    for match in re.finditer(r"\bgh\s+release\s+(view|create|upload|delete|edit|list)\b([^\n;&|]*)", normalized_run):
        command = match.group(1)
        if command in {"delete", "edit", "list"}:
            raise PublicationError("workflow contains an unsupported GitHub Release command")
        try:
            tokens = shlex.split(match.group(2), posix=True)
        except ValueError as exc:
            raise PublicationError("workflow contains malformed release command syntax") from exc
        commands.append((command, tokens))

    topology = _canonical_release_topology(run_blocks) if commands else None
    expected_commands = {"view", "create"}
    if topology is not None and topology["upload_tokens"] is not None:
        expected_commands.add("upload")
    if commands and (topology is None or {command for command, _ in commands} != expected_commands or len(commands) != len(expected_commands)):
        raise PublicationError("workflow GitHub Release commands must use the canonical conditional topology")

    release_view = any(command == "view" for command, _ in commands)
    release_create = any(command == "create" for command, _ in commands)
    release_upload = any(command == "upload" for command, _ in commands)
    upload_clobber = any(command == "upload" and "--clobber" in tokens for command, tokens in commands)
    generate_notes = any(command == "create" and "--generate-notes" in tokens for command, tokens in commands)
    notes_files: list[str] = []
    draft = False
    prerelease = False
    source_patterns: list[str] = []
    for command, tokens in commands:
        if command != "create":
            if command == "upload":
                source_patterns.extend(token for token in tokens if "*" in token or "?" in token or "[" in token)
            continue
        draft = draft or "--draft" in tokens
        prerelease = prerelease or "--prerelease" in tokens
        source_patterns.extend(token for token in tokens if "*" in token or "?" in token or "[" in token)
        for index, token in enumerate(tokens):
            if token == "--notes-file" and index + 1 < len(tokens):
                notes_files.append(tokens[index + 1])
            elif token.startswith("--notes-file="):
                notes_files.append(token.split("=", 1)[1])
    if len(notes_files) > 1 or (generate_notes and notes_files):
        raise PublicationError("workflow declares ambiguous release notes behavior")
    notes_file = notes_files[0] if notes_files else None
    if generate_notes:
        notes_source = "generated"
    elif notes_file == "CHANGELOG.md":
        notes_source = "changelog"
    elif notes_file:
        notes_source = "declared_file"
    else:
        notes_source = "none"

    credential_markers: list[str] = []
    for block in _env_blocks(lines):
        for line in block:
            match = re.match(r"^\s*(GH_TOKEN|GITHUB_TOKEN)\s*:\s*(.*)$", line)
            if match:
                credential_markers.append(match.group(2).strip())
    if any("GH_TOKEN" in line or "GITHUB_TOKEN" in line for line in run_text.splitlines()):
        raise PublicationError("workflow uses an unsupported local credential marker")
    if credential_markers and any(value != "${{ github.token }}" for value in credential_markers):
        raise PublicationError("workflow uses an unsupported credential authority")
    credential_authority = "github.token" if credential_markers else "none"
    has_release = release_view or release_create or release_upload
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "name": name,
        "event": "push",
        "tag_trigger": "explicit_tags_filter" if explicit_patterns else "unfiltered_push",
        "tag_patterns": explicit_patterns,
        "contents_permission": permission_value,
        "github_release": has_release,
        "release_view": release_view,
        "release_create": release_create,
        "release_upload": release_upload,
        "upload_clobber": upload_clobber,
        "canonical_release_topology": topology is not None,
        "credential_authority": credential_authority,
        "notes_source": notes_source,
        "notes_file": notes_file,
        "generate_notes": generate_notes,
        "draft": draft,
        "prerelease": prerelease,
        "release_source_patterns": sorted(set(source_patterns)),
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
