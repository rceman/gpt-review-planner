"""One manifest-validation entry point for current v2 and immutable history."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from gpt_patch_pack_v2_common import (  # re-export current contract primitives
    DEFAULT_COMPATIBILITY,
    DuplicateKey,
    load_json,
    normalized_path,
    sha256,
    validate_compatibility,
    validate_sha,
)
from gpt_patch_pack_v2_common import validate_manifest as validate_v2_manifest


def validate_manifest(value: dict[str, Any], *, pack_root: Path | None = None, allow_historical: bool = False) -> dict[str, Any]:
    if value.get("format") == "gpt-patch-pack-v2":
        return validate_v2_manifest(value, pack_root=pack_root)
    if allow_historical and value.get("format") == "gpt-patch-pack-v1":
        from gpt_patch_pack_v1_common import validate_manifest as validate_v1_manifest
        return validate_v1_manifest(value, pack_root=pack_root)
    raise ValueError("only GPT Patch Pack v2 is supported for new tasks")
