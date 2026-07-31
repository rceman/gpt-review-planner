#!/usr/bin/env python3
"""Validate a GPT Patch Pack v2 archive using the runner boundary."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import tempfile

from gpt_patch_pack_common import load_json, validate_manifest
_SPEC = importlib.util.spec_from_file_location("gpt_patch_pack_runner_v2", Path(__file__).with_name("gpt-patch-pack-runner-v2.py"))
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
extract_archive = _MODULE.extract_archive
verify_checksums = _MODULE.verify_checksums


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="gpt-patch-v2-validate-") as raw:
        root = extract_archive(args.archive.resolve(), Path(raw))
        verify_checksums(root)
        validate_manifest(load_json(root / "MANIFEST.json"), pack_root=root)
    print(f"PASS: {args.archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
