#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from pathlib import Path

FILE_PATTERNS = (
    ".DS_Store",
    "Thumbs.db",
)
DIR_NAMES = (
    "__MACOSX",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "target",
    "dist",
    "build",
    "coverage",
)


def forbidden_file(path: Path) -> bool:
    name = path.name
    return (
        name in FILE_PATTERNS
        or "Zone.Identifier" in name
        or "Zone.Identifier" in name
        or name.endswith(".pyc")
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: clean-archive-files.py DIRECTORY", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    removed: list[Path] = []

    for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and path.name in DIR_NAMES:
            shutil.rmtree(path)
            removed.append(path)
        elif path.is_file() and forbidden_file(path):
            path.unlink()
            removed.append(path)

    for path in sorted(removed):
        print(path.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
