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
    validate_source_output_policy,
)
from gpt_patch_pack_v2_common import validate_manifest as validate_v2_manifest


def validate_manifest(value: dict[str, Any], *, pack_root: Path | None = None) -> dict[str, Any]:
    """Validate the sole active GPT Patch Pack contract.

    Historical v1 records remain readable as Git history, but no active tool
    accepts them as input or exposes a compatibility switch.
    """
    if value.get("format") != "gpt-patch-pack-v2":
        raise ValueError("only GPT Patch Pack v2 is supported")
    return validate_v2_manifest(value, pack_root=pack_root)
