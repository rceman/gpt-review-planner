#!/usr/bin/env python3
"""Validate the bounded, auditable handoff of an executable patch pack."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PATCH_ID_RE = re.compile(r"^patch-\d{8}-\d{6}-[a-z0-9]+(?:-[a-z0-9]+){0,2}$")


class DeliveryError(ValueError):
    pass


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise DeliveryError(f"missing {label}: {path}")
    return path


def validate_response(path: Path, archive: str, sidecar: str) -> None:
    text = path.read_text(encoding="utf-8")
    if not re.search(r"(?m)^PATCH_PACK_NAME\s*$", text) or archive not in text:
        raise DeliveryError("response must declare PATCH_PACK_NAME with the exact archive basename")
    if not re.search(r"(?m)^SHA256_FILE_NAME\s*$", text) or sidecar not in text:
        raise DeliveryError("response must declare SHA256_FILE_NAME with the exact sidecar basename")
    expected = f"## AGENT_HANDOFF\n\nApply patch pack `{archive}` from the Downloads folder."
    handoff = re.search(r"(?ms)^## AGENT_HANDOFF\s*$.*\Z", text)
    if not handoff or handoff.group(0).rstrip() != expected:
        raise DeliveryError("response must end with the exact top-level AGENT_HANDOFF sentence")


def validate(args: argparse.Namespace) -> None:
    root = args.pack_root.resolve()
    planner = args.planner_root.resolve()
    try:
        manifest = json.loads(require_file(root / "manifest.json", "manifest.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DeliveryError(f"invalid manifest.json: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 2:
        raise DeliveryError("manifest.schema_version must be 2")
    patch_id = manifest.get("patch_id")
    if not isinstance(patch_id, str) or not PATCH_ID_RE.fullmatch(patch_id):
        raise DeliveryError("manifest.patch_id must be patch-YYYYMMDD-HHMMSS-<one-to-three-word-slug>")
    archive = f"{patch_id}.tar.gz"
    sidecar = f"{archive}.sha256"
    if args.archive_name != archive:
        raise DeliveryError(f"archive name must be derived from manifest.patch_id: {archive}")
    if args.sidecar_name != sidecar:
        raise DeliveryError(f"sidecar name must be archive basename plus .sha256: {sidecar}")
    prompt = require_file(root / "AGENT_PROMPT.md", "AGENT_PROMPT.md").read_text(encoding="utf-8")
    sentence = f"Apply patch pack `{archive}` from the Downloads folder."
    if sentence not in prompt:
        raise DeliveryError("AGENT_PROMPT.md must contain the exact archive handoff sentence")
    for name in ("patch_pack_scope.py", "verify-agent-evidence.py"):
        bundled = require_file(root / "scripts" / name, f"bundled {name}")
        canonical = require_file(planner / "scripts" / name, f"planner {name}")
        if bundled.read_bytes() != canonical.read_bytes():
            raise DeliveryError(f"bundled {name} is not byte-identical to the pinned planner tool")
        result = subprocess.run([sys.executable, str(bundled), "--help"], capture_output=True, text=True)
        if result.returncode != 0:
            raise DeliveryError(f"bundled {name} failed --help (exit {result.returncode})")
    if args.response_file:
        validate_response(args.response_file, archive, sidecar)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-root", type=Path, required=True)
    parser.add_argument("--planner-root", type=Path, required=True)
    parser.add_argument("--archive-name", required=True)
    parser.add_argument("--sidecar-name", required=True)
    parser.add_argument("--response-file", type=Path)
    args = parser.parse_args()
    try:
        validate(args)
    except (DeliveryError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Patch-pack delivery validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
