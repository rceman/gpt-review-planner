#!/usr/bin/env python3
"""Validate provenance metadata embedded in a prepared project archive."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")
UTC_RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
ABSOLUTE_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[\\/]|file://)")
EXPECTED_WORKFLOWS = {"review-and-implement", "review-only"}


class ManifestError(ValueError):
    pass


def object_field(data: dict[str, Any], key: str, label: str) -> Any:
    if key not in data:
        raise ManifestError(f"{label} is missing {key}")
    return data[key]


def string_field(data: dict[str, Any], key: str, label: str, *, empty: bool = False) -> str:
    value = object_field(data, key, label)
    if not isinstance(value, str) or (not empty and not value):
        raise ManifestError(f"{label}.{key} must be a non-empty string")
    return value


def nullable_string(data: dict[str, Any], key: str, label: str) -> str | None:
    value = object_field(data, key, label)
    if value is not None and (not isinstance(value, str) or not value):
        raise ManifestError(f"{label}.{key} must be a string or null")
    return value


def boolean_field(data: dict[str, Any], key: str, label: str) -> bool:
    value = object_field(data, key, label)
    if type(value) is not bool:
        raise ManifestError(f"{label}.{key} must be a JSON boolean")
    return value


def reject_absolute(value: str | None, label: str) -> None:
    if value is not None and ABSOLUTE_PATH_RE.match(value):
        raise ManifestError(f"{label} must not contain an absolute local path")


def validate_archive_root(value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ManifestError("archive.root must be a non-empty string")
    if value != value.strip():
        raise ManifestError("archive.root must not have leading or trailing whitespace")
    if value.lower().startswith("file://"):
        raise ManifestError("archive.root must not use a file URI")
    if re.match(r"^[A-Za-z]:", value):
        raise ManifestError("archive.root must not use a Windows drive prefix")
    if any(ord(character) < 0x20 for character in value):
        raise ManifestError("archive.root must not contain ASCII control characters")
    if "/" in value or "\\" in value or value in {".", ".."}:
        raise ManifestError("archive.root must be a normalized relative archive root")


def validate(manifest_path: Path, project_root: Path | None, staging: bool) -> None:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"unable to read valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a JSON object")
    if data.get("schema_version") != 1:
        raise ManifestError("schema_version must equal 1")

    source = object_field(data, "source", "manifest")
    workflow = object_field(data, "workflow", "manifest")
    review = object_field(data, "review", "manifest")
    archive = object_field(data, "archive", "manifest")
    for value, label in ((source, "source"), (workflow, "workflow"), (review, "review"), (archive, "archive")):
        if not isinstance(value, dict):
            raise ManifestError(f"manifest.{label} must be an object")

    repository = nullable_string(source, "repository", "source")
    branch = nullable_string(source, "branch", "source")
    revision = nullable_string(source, "revision", "source")
    dirty = boolean_field(source, "dirty", "source")
    dirty_included = boolean_field(source, "dirty_included_by_owner", "source")
    reject_absolute(repository, "source.repository")
    reject_absolute(branch, "source.branch")
    reject_absolute(revision, "source.revision")
    if dirty_included and not dirty:
        raise ManifestError("source.dirty_included_by_owner requires source.dirty=true")

    lock_path = string_field(workflow, "lock_path", "workflow")
    pinned_repository = string_field(workflow, "repository", "workflow")
    pinned_version = string_field(workflow, "version", "workflow")
    pinned_commit = string_field(workflow, "commit", "workflow")
    document = string_field(workflow, "document", "workflow")
    if lock_path != ".gpt-workflow.lock":
        raise ManifestError("workflow.lock_path must be .gpt-workflow.lock")
    if not COMMIT_RE.fullmatch(pinned_commit):
        raise ManifestError("workflow.commit must be exactly 40 hexadecimal characters")
    for value, label in ((pinned_repository, "workflow.repository"), (pinned_version, "workflow.version"), (document, "workflow.document")):
        reject_absolute(value, label)

    expected_workflow = string_field(review, "expected_workflow", "review")
    task_objective = string_field(review, "task_objective", "review", empty=True)
    if expected_workflow not in EXPECTED_WORKFLOWS:
        raise ManifestError("review.expected_workflow must be review-and-implement or review-only")
    reject_absolute(task_objective, "review.task_objective")

    archive_root = string_field(archive, "root", "archive")
    validate_archive_root(archive_root)
    generated_at = string_field(archive, "generated_at", "archive")
    source_modified = boolean_field(archive, "source_modified", "archive")
    if not UTC_RFC3339_RE.fullmatch(generated_at):
        raise ManifestError("archive.generated_at must be a UTC RFC3339 timestamp ending in Z")
    if staging and source_modified:
        raise ManifestError("archive.source_modified must be false in staging mode")

    if project_root is None:
        project_root = manifest_path.parent.parent
    lock_file = project_root / lock_path
    try:
        lock = json.loads(lock_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"unable to read adjacent workflow lock: {exc}") from exc
    if not isinstance(lock, dict):
        raise ManifestError("adjacent workflow lock must be a JSON object")
    for key, expected in (
        ("repository", pinned_repository),
        ("version", pinned_version),
        ("commit", pinned_commit),
        ("document", document),
    ):
        if lock.get(key) != expected:
            raise ManifestError(f"workflow.{key} does not match adjacent .gpt-workflow.lock")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--project-root", type=Path, help="staged project root containing .gpt-workflow.lock")
    parser.add_argument("--staging", action="store_true", help="enforce archive.source_modified=false")
    args = parser.parse_args()
    try:
        validate(args.manifest, args.project_root, args.staging)
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: archive manifest {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
