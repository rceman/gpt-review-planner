"""Shared strict primitives for GPT Patch Pack v1."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from pathlib import Path

FORMAT = "gpt-patch-pack-v1"
RUNNER_VERSION = "1.0.0"
DEFAULT_COMPATIBILITY = {
    "scope": "none", "authorized": False,
    "canonical_implementation": "GPT Patch Pack v1",
    "legacy_behavior": "unsupported and out of scope",
    "authorization_source": None, "supported_legacy_versions": [],
    "direction": "none", "removal_condition": None,
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PATCH_ID_RE = re.compile(r"^patch-[0-9]{8}-[0-9]{6}-[a-z0-9](?:[a-z0-9-]{0,63})$")
SEMVER_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique)

def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out

def normalized_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        raise ValueError("path is not canonical")
    p = PurePosixPath(value)
    if p.as_posix() != value or "." in p.parts or ".." in p.parts:
        raise ValueError("path is not canonical")
    return value

def validate_sha(value: str) -> str:
    if not SHA_RE.fullmatch(value):
        raise ValueError("invalid Git SHA")
    return value

def sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def validate_compatibility(value):
    if value == DEFAULT_COMPATIBILITY:
        return value
    if not isinstance(value, dict) or value.get("authorized") is not True:
        raise ValueError("compatibility authorization is incomplete")
    required = {"scope", "authorized", "canonical_implementation", "legacy_behavior",
                "authorization_source", "supported_legacy_versions", "direction", "removal_condition"}
    if set(value) != required or value["scope"] == "none" or not value["authorization_source"]:
        raise ValueError("compatibility authorization is incomplete")
    if not value["supported_legacy_versions"] or value["direction"] == "none":
        raise ValueError("compatibility authorization is incomplete")
    if not value["removal_condition"]:
        raise ValueError("compatibility removal condition is required")
    return value

def validate_manifest(value, *, pack_root=None):
    """Single strict manifest contract shared by all v1 consumers."""
    if not isinstance(value, dict):
        raise ValueError("manifest must be an object")
    required = {"schema_version","format","patch_id","title","description","created_at",
                "runner_version","baseline_release","evidence_directory","workflow","target",
                "payload","files_created","files_modified","files_deleted","target_tree",
                "requirements","gates","compatibility","metadata"}
    if set(value) != required:
        raise ValueError("manifest keys invalid")
    if value["schema_version"] != 2 or value["format"] != FORMAT or value["runner_version"] != RUNNER_VERSION:
        raise ValueError("manifest version or format invalid")
    if not isinstance(value["patch_id"], str) or not PATCH_ID_RE.fullmatch(value["patch_id"]):
        raise ValueError("invalid patch_id")
    if not isinstance(value["baseline_release"], str) or not SEMVER_RE.fullmatch(value["baseline_release"]):
        raise ValueError("invalid baseline release")
    expected_evidence = f".gpt-review/evidence/{value['baseline_release']}/{value['patch_id']}"
    if value["evidence_directory"] != expected_evidence:
        raise ValueError("evidence directory identity mismatch")
    workflow = value["workflow"]
    if not isinstance(workflow, dict) or set(workflow) != {"repository","version","commit","document"}:
        raise ValueError("workflow keys invalid")
    if workflow["repository"] != "https://github.com/rceman/gpt-review-planner" or workflow["document"] != "GPT_REVIEW_PLANNER.md":
        raise ValueError("workflow identity mismatch")
    validate_sha(workflow["commit"])
    target = value["target"]
    if not isinstance(target, dict) or set(target) != {"repository","accepted_origin_urls","branch","base_revision","remote","remote_ref"}:
        raise ValueError("target keys invalid")
    validate_sha(target["base_revision"])
    if not isinstance(target["accepted_origin_urls"], list) or not target["accepted_origin_urls"]:
        raise ValueError("accepted origins invalid")
    if not isinstance(target["remote_ref"], str) or not target["remote_ref"].startswith("refs/remotes/"):
        raise ValueError("remote ref invalid")
    payload = value["payload"]
    if payload != {"patch":"payload/changes.patch","format":"git-binary-full-index"}:
        raise ValueError("payload contract invalid")
    classes=[]
    for key in ("files_created","files_modified","files_deleted"):
        if not isinstance(value[key], list): raise ValueError(f"{key} invalid")
        normalized=[normalized_path(x) for x in value[key]]
        if normalized != sorted(set(normalized)): raise ValueError(f"{key} not sorted or unique")
        classes.append(set(normalized))
    if classes[0]&classes[1] or classes[0]&classes[2] or classes[1]&classes[2]:
        raise ValueError("file operation classes overlap")
    validate_sha(value["target_tree"])
    req_ids=[]
    for item in value["requirements"]:
        if not isinstance(item,dict) or set(item)!={"id","summary","acceptance"} or not isinstance(item["id"],str) or not re.fullmatch(r"REQ-[A-Za-z0-9][A-Za-z0-9-]*",item["id"]):
            raise ValueError("invalid requirement")
        if not isinstance(item["acceptance"],list) or not item["acceptance"]: raise ValueError("invalid requirement acceptance")
        req_ids.append(item["id"])
    if len(req_ids)!=len(set(req_ids)): raise ValueError("duplicate requirement ID")
    gate_ids=[]
    for gate in value["gates"]:
        if not isinstance(gate,dict) or set(gate)!={"id","name","kind","argv","env","timeout_seconds","max_output_bytes"}:
            raise ValueError("invalid gate")
        if gate["kind"]!="command" or not isinstance(gate["argv"],list) or not gate["argv"] or any(not isinstance(x,str) or not x for x in gate["argv"]): raise ValueError("invalid gate command")
        if gate["argv"][0] in {"true","false","echo"} or (gate["argv"][0] in {"sh","bash","python3"} and len(gate["argv"])>1 and gate["argv"][1] in {"-c","-e"}): raise ValueError("placeholder gate command")
        if not isinstance(gate["env"],dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in gate["env"].items()): raise ValueError("invalid gate environment")
        if not isinstance(gate["timeout_seconds"],int) or not 1<=gate["timeout_seconds"]<=7200 or not isinstance(gate["max_output_bytes"],int) or not 1024<=gate["max_output_bytes"]<=16777216: raise ValueError("gate limits invalid")
        gate_ids.append(gate["id"])
    if not gate_ids or len(gate_ids)!=len(set(gate_ids)): raise ValueError("invalid gate IDs")
    validate_compatibility(value["compatibility"])
    if not isinstance(value["metadata"],dict) or set(value["metadata"])!={"planner_commit","gpt_static_checks_performed","gpt_runtime_checks_not_performed"}: raise ValueError("metadata invalid")
    validate_sha(value["metadata"]["planner_commit"])
    if pack_root is not None:
        root = Path(pack_root)
        if not (root/"AGENT_TASK.md").is_file() or (root/"AGENT_TASK.md").is_symlink() or not (root/"payload/changes.patch").is_file(): raise ValueError("canonical pack payload missing")
    return value
