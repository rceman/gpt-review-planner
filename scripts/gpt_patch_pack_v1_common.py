"""Shared strict primitives for GPT Patch Pack v1."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath

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
