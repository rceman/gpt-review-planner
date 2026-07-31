"""Canonical strict GPT Patch Pack v2 manifest and archive contract."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

FORMAT = "gpt-patch-pack-v2"
RUNNER_VERSION = "2.0.0"
MODES = {"gpt_tunnel_managed", "repository_evidence"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SEMVER_RE = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
PATCH_ID_RE = re.compile(r"^patch-[0-9]{8}-[0-9]{6}-[a-z0-9](?:[a-z0-9-]{0,63})$")
ALLOWED_MANIFEST = {
    "schema_version", "format", "patch_id", "title", "description", "created_at",
    "runner_version", "baseline_release", "execution_mode", "evidence_directory",
    "workflow", "target", "payload", "files_created", "files_modified", "files_deleted",
    "target_tree", "requirements", "gates", "compatibility", "metadata",
}
REQUIRED_COMMON = ALLOWED_MANIFEST - {"evidence_directory"}
DEFAULT_COMPATIBILITY = {
    "scope": "none", "authorized": False, "canonical_implementation": "GPT Patch Pack v2",
    "legacy_behavior": "unsupported and out of scope", "authorization_source": None,
    "supported_legacy_versions": [], "direction": "none", "removal_condition": None,
}


class DuplicateKey(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DuplicateKey(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKey) as exc:
        raise ValueError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def normalized_path(value: Any, label: str = "path") -> str:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        raise ValueError(f"{label} is not a normalized relative POSIX path")
    p = PurePosixPath(value)
    if p.as_posix() != value or "." in p.parts or ".." in p.parts:
        raise ValueError(f"{label} is not a normalized relative POSIX path")
    return value


def validate_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase 40-character Git SHA")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_compatibility(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("compatibility must be an object")
    keys = set(DEFAULT_COMPATIBILITY)
    if set(value) != keys:
        raise ValueError("compatibility declaration keys are invalid")
    if value == DEFAULT_COMPATIBILITY:
        return value
    if value["authorized"] is not True or value["scope"] == "none":
        raise ValueError("unauthorized compatibility must use the empty scope=none declaration")
    if not isinstance(value["scope"], str) or not value["scope"].strip():
        raise ValueError("authorized compatibility scope is required")
    if not isinstance(value["authorization_source"], str) or not value["authorization_source"].strip():
        raise ValueError("authorized compatibility authorization_source is required")
    versions = value["supported_legacy_versions"]
    if not isinstance(versions, list) or not versions or any(not isinstance(x, str) or not x.strip() for x in versions):
        raise ValueError("authorized compatibility supported_legacy_versions is required")
    if value["direction"] not in {"forward", "backward", "bidirectional"}:
        raise ValueError("authorized compatibility direction is invalid")
    if not isinstance(value["removal_condition"], str) or not value["removal_condition"].strip():
        raise ValueError("authorized compatibility removal_condition is required")
    if not isinstance(value["canonical_implementation"], str) or not isinstance(value["legacy_behavior"], str):
        raise ValueError("compatibility descriptions must be strings")
    return value


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{label} keys are invalid")
    return value


def validate_manifest(value: dict[str, Any], *, pack_root: Path | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or (set(value) != REQUIRED_COMMON and set(value) != ALLOWED_MANIFEST):
        raise ValueError("manifest keys are invalid")
    if value["schema_version"] != 2 or value["format"] != FORMAT or value["runner_version"] != RUNNER_VERSION:
        raise ValueError("manifest format or runner version is invalid")
    if not isinstance(value["patch_id"], str) or not PATCH_ID_RE.fullmatch(value["patch_id"]):
        raise ValueError("invalid patch_id")
    if not isinstance(value["title"], str) or not value["title"].strip() or not isinstance(value["description"], str) or not value["description"].strip():
        raise ValueError("title and description are required")
    if not isinstance(value["created_at"], str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value["created_at"]):
        raise ValueError("created_at must be an RFC3339 UTC timestamp")
    if not isinstance(value["baseline_release"], str) or not SEMVER_RE.fullmatch(value["baseline_release"]):
        raise ValueError("baseline_release must be strict semver with v prefix")
    mode = value["execution_mode"]
    if mode not in MODES:
        raise ValueError("execution_mode must be explicit")
    if mode == "gpt_tunnel_managed" and "evidence_directory" in value:
        raise ValueError("tunnel mode must not declare evidence_directory")
    if mode == "repository_evidence":
        evidence = value.get("evidence_directory")
        expected = f".gpt-review/evidence/{value['baseline_release']}/{value['patch_id']}"
        if evidence != expected:
            raise ValueError("repository evidence_directory is invalid")
    workflow = _exact(value["workflow"], {"repository", "version", "commit", "document"}, "workflow")
    if workflow["repository"] != "https://github.com/rceman/gpt-review-planner" or workflow["document"] != "GPT_REVIEW_PLANNER.md":
        raise ValueError("workflow identity is invalid")
    if not isinstance(workflow["version"], str) or not SEMVER_RE.fullmatch(workflow["version"]):
        raise ValueError("workflow version is invalid")
    validate_sha(workflow["commit"], "workflow.commit")
    target = _exact(value["target"], {"repository", "accepted_origin_urls", "branch", "base_revision", "remote", "remote_ref"}, "target")
    if not isinstance(target["repository"], str) or not target["repository"].strip() or not isinstance(target["accepted_origin_urls"], list) or not target["accepted_origin_urls"]:
        raise ValueError("target identity is invalid")
    validate_sha(target["base_revision"], "target.base_revision")
    if not isinstance(target["branch"], str) or not target["branch"] or not isinstance(target["remote"], str) or not target["remote"] or not isinstance(target["remote_ref"], str) or not target["remote_ref"].startswith("refs/remotes/"):
        raise ValueError("target refs are invalid")
    if value["payload"] != {"patch": "payload/changes.patch", "format": "git-binary-full-index"}:
        raise ValueError("payload contract is invalid")
    classes: list[set[str]] = []
    for key in ("files_created", "files_modified", "files_deleted"):
        paths = value[key]
        if not isinstance(paths, list):
            raise ValueError(f"{key} must be an array")
        normalized = [normalized_path(path, key) for path in paths]
        if normalized != sorted(set(normalized)):
            raise ValueError(f"{key} must be sorted and unique")
        classes.append(set(normalized))
    if classes[0] & classes[1] or classes[0] & classes[2] or classes[1] & classes[2]:
        raise ValueError("file operation classes overlap")
    validate_sha(value["target_tree"], "target_tree")
    requirements = value["requirements"]
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("requirements must be non-empty")
    req_ids: list[str] = []
    for item in requirements:
        item = _exact(item, {"id", "summary", "acceptance"}, "requirement")
        if not isinstance(item["id"], str) or not re.fullmatch(r"REQ-[A-Za-z0-9][A-Za-z0-9-]*", item["id"]):
            raise ValueError("requirement ID is invalid")
        if not isinstance(item["summary"], str) or not item["summary"].strip() or not isinstance(item["acceptance"], list) or not item["acceptance"] or any(not isinstance(x, str) or not x.strip() for x in item["acceptance"]):
            raise ValueError("requirement is invalid")
        req_ids.append(item["id"])
    if len(req_ids) != len(set(req_ids)):
        raise ValueError("duplicate requirement ID")
    gate_ids: list[str] = []
    for gate in value["gates"]:
        gate = _exact(gate, {"id", "name", "kind", "argv", "env", "timeout_seconds", "max_output_bytes"}, "gate")
        if not isinstance(gate["id"], str) or not gate["id"] or gate["id"] in gate_ids:
            raise ValueError("gate ID is invalid or duplicate")
        if gate["kind"] != "command" or not isinstance(gate["argv"], list) or not gate["argv"] or any(not isinstance(x, str) or not x for x in gate["argv"]):
            raise ValueError("gate command is invalid")
        if gate["argv"][0] in {"true", "false", "echo"}:
            raise ValueError("placeholder gate command is forbidden")
        if not isinstance(gate["env"], dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in gate["env"].items()):
            raise ValueError("gate environment is invalid")
        if not isinstance(gate["timeout_seconds"], int) or isinstance(gate["timeout_seconds"], bool) or not 1 <= gate["timeout_seconds"] <= 7200 or not isinstance(gate["max_output_bytes"], int) or isinstance(gate["max_output_bytes"], bool) or not 1024 <= gate["max_output_bytes"] <= 16777216:
            raise ValueError("gate bounds are invalid")
        gate_ids.append(gate["id"])
    if not gate_ids:
        raise ValueError("gates must be non-empty")
    validate_compatibility(value["compatibility"])
    metadata = _exact(value["metadata"], {"planner_commit", "gpt_static_checks_performed", "gpt_runtime_checks_not_performed"}, "metadata")
    validate_sha(metadata["planner_commit"], "metadata.planner_commit")
    for key in ("gpt_static_checks_performed", "gpt_runtime_checks_not_performed"):
        if not isinstance(metadata[key], list) or any(not isinstance(x, str) or not x.strip() for x in metadata[key]):
            raise ValueError(f"metadata.{key} is invalid")
    if pack_root is not None:
        for relative in ("MANIFEST.json", "SHA256SUMS", "AGENT_TASK.md", "payload/changes.patch"):
            path = pack_root / relative
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"missing canonical pack file: {relative}")
        try:
            (pack_root / "AGENT_TASK.md").read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError("AGENT_TASK.md must be regular UTF-8") from exc
    return value
