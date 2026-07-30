#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--patch", required=True, type=Path)
    args = parser.parse_args()
    patch = args.patch.resolve()
    if not patch.is_file() or patch.stat().st_size == 0:
        print("ERROR: patch missing or empty", file=sys.stderr)
        return 1
    command = ["git", "apply", "--index", "--binary", str(patch)]
    if args.check:
        command.insert(2, "--check")
    proc = subprocess.run(command)
    if proc.returncode:
        return proc.returncode
    if args.apply:
        print("GPT_PATCH_PAYLOAD_APPLIED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
