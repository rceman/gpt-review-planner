#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/build-offline-rust-bundle.sh [options]

Options:
  --toolchain NAME   Rust toolchain/channel. Default: stable.
  --output-dir DIR   Output directory. Default: ./dist.
  -h, --help         Show this help.

Produces:
  rustc-lite-<rust-version>-<host>.tar.zst
  rustc-lite-<rust-version>-<host>.tar.zst.sha256
  rustc-lite-manifest.json
USAGE
}

fail() {
  printf '[build-offline-rust-bundle] error: %s\n' "$*" >&2
  exit 1
}

log() {
  printf '[build-offline-rust-bundle] %s\n' "$*" >&2
}

toolchain='stable'
output_dir="$PWD/dist"
while (($# > 0)); do
  case "$1" in
    --toolchain)
      (($# >= 2)) || fail '--toolchain requires a value'
      toolchain="$2"
      shift 2
      ;;
    --output-dir)
      (($# >= 2)) || fail '--output-dir requires a directory'
      output_dir="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

command -v rustup >/dev/null 2>&1 || fail 'rustup is required to build the bundle'
command -v tar >/dev/null 2>&1 || fail 'tar is required'
command -v zstd >/dev/null 2>&1 || fail 'zstd is required'
command -v python3 >/dev/null 2>&1 || fail 'python3 is required'

case "$toolchain" in
  *[!A-Za-z0-9._+-]*) fail "unsafe toolchain value: $toolchain" ;;
esac

mkdir -p "$output_dir"
output_dir="$(cd "$output_dir" && pwd -P)"
temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' EXIT

export RUSTUP_HOME="$temporary/rustup"
mkdir -p "$RUSTUP_HOME"
log "installing isolated '$toolchain' toolchain with minimal profile"
rustup toolchain install "$toolchain" --profile minimal

rustc_vv="$(rustup run "$toolchain" rustc -Vv)"
rust_release="$(printf '%s\n' "$rustc_vv" | sed -n 's/^release: //p')"
host="$(printf '%s\n' "$rustc_vv" | sed -n 's/^host: //p')"
commit_hash="$(printf '%s\n' "$rustc_vv" | sed -n 's/^commit-hash: //p')"
[[ -n "$rust_release" && -n "$host" ]] || fail 'could not resolve Rust release and host'

sysroot="$(rustup run "$toolchain" rustc --print sysroot)"
bundle_name="rustc-lite-$rust_release-$host"
stage="$temporary/stage/$bundle_name"
mkdir -p "$stage"
cp -a "$sysroot"/. "$stage"/

# Minimal profile should not contain HTML docs, but remove them defensively.
rm -rf "$stage/share/doc/rust/html" 2>/dev/null || true

RUST_RELEASE="$rust_release" HOST="$host" COMMIT_HASH="$commit_hash" TOOLCHAIN="$toolchain" \
python3 - "$stage/manifest.json" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone

path = sys.argv[1]
data = {
    "format": "gpt-review-planner-rustc-lite-v1",
    "requested_toolchain": os.environ["TOOLCHAIN"],
    "rust_release": os.environ["RUST_RELEASE"],
    "host": os.environ["HOST"],
    "commit_hash": os.environ["COMMIT_HASH"],
    "components": ["rustc", "rust-std", "cargo"],
    "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
    handle.write("\n")
PY

"$stage/bin/rustc" --version
"$stage/bin/cargo" --version

archive="$output_dir/$bundle_name.tar.zst"
checksum="$archive.sha256"
release_manifest="$output_dir/rustc-lite-manifest.json"
rm -f "$archive" "$checksum" "$release_manifest"
log "creating $archive"
tar --zstd -cf "$archive" -C "$temporary/stage" "$bundle_name"

archive_basename="$(basename "$archive")"
checksum_basename="$(basename "$checksum")"
archive_sha256="$(sha256sum "$archive" | awk '{print $1}')"
printf '%s  %s\n' "$archive_sha256" "$archive_basename" > "$checksum"

RUST_RELEASE="$rust_release" HOST="$host" COMMIT_HASH="$commit_hash" \
TOOLCHAIN="$toolchain" ARCHIVE_BASENAME="$archive_basename" \
CHECKSUM_BASENAME="$checksum_basename" ARCHIVE_SHA256="$archive_sha256" \
ARCHIVE_SIZE="$(stat -c %s "$archive")" \
python3 - "$release_manifest" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone

path = sys.argv[1]
data = {
    "format": "gpt-review-planner-rustc-release-v1",
    "requested_toolchain": os.environ["TOOLCHAIN"],
    "rust_release": os.environ["RUST_RELEASE"],
    "host": os.environ["HOST"],
    "commit_hash": os.environ["COMMIT_HASH"],
    "bundle": os.environ["ARCHIVE_BASENAME"],
    "checksum": os.environ["CHECKSUM_BASENAME"],
    "sha256": os.environ["ARCHIVE_SHA256"],
    "size_bytes": int(os.environ["ARCHIVE_SIZE"]),
    "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
    handle.write("\n")
PY

log "bundle ready"
printf '%s\n' "$archive"
printf '%s\n' "$checksum"
printf '%s\n' "$release_manifest"
