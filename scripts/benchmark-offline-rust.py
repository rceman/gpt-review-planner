#!/usr/bin/env python3
"""Verify and benchmark a downloaded rustc-lite Actions artifact offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOTSTRAP = ROOT / "scripts/bootstrap-rustc.sh"
DEFAULT_KERNEL = ROOT / "examples/rust-domain-feature/overlay/src/damage_kernel.rs"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_bundle(directory: Path) -> Path:
    bundles = sorted(directory.rglob("rustc-lite-*.tar.zst"))
    if len(bundles) != 1:
        raise SystemExit(
            f"expected exactly one rustc-lite .tar.zst under {directory}, found {len(bundles)}"
        )
    return bundles[0]


def verify_bundle(bundle: Path) -> str:
    checksum = Path(f"{bundle}.sha256")
    if not checksum.is_file():
        raise SystemExit(f"missing checksum sidecar: {checksum}")
    tokens = checksum.read_text(encoding="utf-8").split()
    if not tokens or len(tokens[0]) != 64:
        raise SystemExit(f"invalid checksum sidecar: {checksum}")
    expected = tokens[0].lower()
    actual = sha256(bundle)
    if actual != expected:
        raise SystemExit(f"SHA-256 mismatch: expected {expected}, got {actual}")
    return actual


def run_bootstrap(
    bootstrap: Path,
    cache: Path,
    kernel: Path,
    binary: Path,
    bundle: Path | None,
) -> float:
    shell_command = "\n".join(
        [
            "set -euo pipefail",
            "rustc --version",
            "cargo --version",
            f"rustc --edition=2021 --test {shlex.quote(str(kernel))} -o {shlex.quote(str(binary))}",
            shlex.quote(str(binary)),
        ]
    )
    command = [
        "bash",
        str(bootstrap),
        "--force-managed",
        "--no-network",
        "--cache-dir",
        str(cache),
    ]
    if bundle is not None:
        command.extend(["--offline-bundle", str(bundle)])
    # Use a non-login shell. `bash -l` may replace PATH and hide the compiler
    # that bootstrap-rustc.sh just prepended.
    command.extend(["--", "bash", "-c", shell_command])

    started = time.perf_counter()
    subprocess.run(command, check=True)
    return time.perf_counter() - started


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--artifact-zip", type=Path)
    source.add_argument("--bundle", type=Path)
    parser.add_argument("--bootstrap", type=Path, default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--kernel", type=Path, default=DEFAULT_KERNEL)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    bootstrap = args.bootstrap.resolve()
    kernel = args.kernel.resolve()
    if not bootstrap.is_file():
        raise SystemExit(f"bootstrap script not found: {bootstrap}")
    if not kernel.is_file():
        raise SystemExit(f"Rust kernel not found: {kernel}")

    with tempfile.TemporaryDirectory(prefix="gpt-rust-benchmark-") as temp_name:
        work = Path(temp_name)
        zip_extract_seconds = 0.0
        if args.artifact_zip is not None:
            artifact = args.artifact_zip.resolve()
            extracted = work / "artifact"
            extracted.mkdir()
            started = time.perf_counter()
            with zipfile.ZipFile(artifact) as archive:
                archive.extractall(extracted)
            zip_extract_seconds = time.perf_counter() - started
            bundle = find_bundle(extracted)
            artifact_size = artifact.stat().st_size
        else:
            bundle = args.bundle.resolve()
            artifact_size = None

        checksum = verify_bundle(bundle)
        cache = (args.cache_dir or (work / "cache")).resolve()
        shutil.rmtree(cache, ignore_errors=True)
        binary = work / "kernel-tests"

        cold_seconds = run_bootstrap(bootstrap, cache, kernel, binary, bundle)
        binary.unlink(missing_ok=True)
        warm_seconds = run_bootstrap(bootstrap, cache, kernel, binary, None)

        result = {
            "artifact_zip": str(args.artifact_zip.resolve()) if args.artifact_zip else None,
            "artifact_zip_size_bytes": artifact_size,
            "artifact_zip_extract_seconds": round(zip_extract_seconds, 6),
            "bundle": bundle.name,
            "bundle_size_bytes": bundle.stat().st_size,
            "bundle_sha256": checksum,
            "kernel": str(kernel),
            "cold_bootstrap_compile_test_seconds": round(cold_seconds, 6),
            "warm_cache_compile_test_seconds": round(warm_seconds, 6),
        }
        rendered = json.dumps(result, indent=2)
        print(rendered)
        if args.json_output:
            args.json_output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
