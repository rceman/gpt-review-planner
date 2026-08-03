#!/usr/bin/env python3
"""Black-box and byte-identity conformance check for project release tooling."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REQUIRED_COMMANDS = {
    "check",
    "check-source",
    "check-release-ready",
    "check-tag-ready",
    "prepare",
    "commit",
    "tag",
    "verify-tag",
}


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-script", required=True, type=Path)
    parser.add_argument(
        "--canonical-script",
        type=Path,
        default=Path(__file__).resolve().with_name("release.py"),
    )
    args = parser.parse_args(argv)
    release_script = args.release_script.resolve()
    canonical_script = args.canonical_script.resolve()
    for label, path in (("release script", release_script), ("canonical script", canonical_script)):
        if path.is_symlink() or not path.is_file():
            return fail(f"{label} must be a regular file: {path}")
    try:
        if release_script.read_bytes() != canonical_script.read_bytes():
            return fail("project release script is not byte-identical to the planner canonical script")
    except OSError as exc:
        return fail(f"cannot read release script: {exc}")
    try:
        result = subprocess.run(
            [sys.executable, str(release_script), "--help"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        return fail(f"release script could not be executed: {exc}")
    if result.returncode != 0:
        return fail("release script --help failed: " + (result.stderr.strip() or "unknown error"))
    commands = set()
    marker = "{check,check-source,check-release-ready,check-tag-ready,prepare,commit,tag,verify-tag}"
    if marker in result.stdout:
        commands.update(REQUIRED_COMMANDS)
    else:
        return fail("release script help does not advertise the canonical lifecycle commands")
    missing = sorted(REQUIRED_COMMANDS - commands)
    if missing:
        return fail("release script is missing lifecycle commands: " + ", ".join(missing))
    print(f"PASS: release tool conforms to {canonical_script}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
