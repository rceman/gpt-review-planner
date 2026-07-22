#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import sys
import tempfile
import zipfile
from pathlib import Path

FORBIDDEN_PARTS = {
    "__MACOSX",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "target",
    "dist",
    "build",
    "coverage",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify-archive.py ARCHIVE.zip", file=sys.stderr)
        return 2

    archive = Path(sys.argv[1]).resolve()
    errors: list[str] = []

    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        for name in names:
            parts = set(Path(name).parts)
            if parts & FORBIDDEN_PARTS:
                errors.append(f"forbidden path: {name}")
            if "Zone.Identifier" in name or "Zone.Identifier" in name:
                errors.append(f"forbidden ADS artifact: {name}")

        with tempfile.TemporaryDirectory() as temp_dir:
            zf.extractall(temp_dir)
            extracted = Path(temp_dir)
            required = [
                "GPT_REVIEW_PLANNER.md",
                "README.md",
                "setup.sh",
                "update.sh",
                "VERSION",
            ]
            top_dirs = [p for p in extracted.iterdir() if p.is_dir()]
            base = top_dirs[0] if len(top_dirs) == 1 else extracted
            for rel in required:
                if not (base / rel).is_file():
                    errors.append(f"missing required extracted file: {rel}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"PASS: {archive}")
    print(f"SHA-256: {sha256(archive)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
