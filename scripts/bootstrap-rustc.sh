#!/usr/bin/env bash
set -euo pipefail

# Fast Rust compiler bootstrap for standalone, dependency-free validation.
#
# Priority:
#   1. Existing rustc, unless --force-managed is requested.
#   2. Previously extracted offline toolchain cache.
#   3. Explicit or repository-bundled offline toolchain archive.
#   4. Optional bundle URL.
#   5. Official rustup minimal-profile network bootstrap.

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/bootstrap-rustc.sh [options] [-- command [args...]]

Options:
  --project DIR          Project whose rust-toolchain file should be inspected.
                         Default: current directory.
  --toolchain NAME       Rust toolchain/channel for rustup fallback.
  --cache-dir DIR        Persistent cache root.
                         Default: $XDG_CACHE_HOME/gpt-review-planner or
                                  $HOME/.cache/gpt-review-planner.
  --offline-bundle FILE  Local rustc-lite .tar.zst archive.
  --bundle-url URL       Download a rustc-lite archive and URL.sha256 sidecar.
  --no-network           Never download. Fail unless system/cache/bundle works.
  --force-managed        Ignore a system rustc and use cache/bundle/bootstrap.
  --print-env            Print shell exports after bootstrap.
  -h, --help             Show this help.

Examples:
  bash scripts/bootstrap-rustc.sh

  bash scripts/bootstrap-rustc.sh \
    --force-managed \
    --no-network \
    --offline-bundle /tmp/rustc-lite.tar.zst \
    -- rustc --version

  bash scripts/bootstrap-rustc.sh -- \
    rustc --edition=2021 --test src/kernel.rs -o /tmp/kernel-tests
USAGE
}

log() {
  printf '[bootstrap-rustc] %s\n' "$*" >&2
}

fail() {
  printf '[bootstrap-rustc] error: %s\n' "$*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/.." && pwd -P)"
project_dir="$PWD"
toolchain=""
cache_dir="${GPT_REVIEW_PLANNER_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/gpt-review-planner}"
offline_bundle=""
bundle_url="${GPT_RUSTC_BUNDLE_URL:-}"
force_managed=0
print_env=0
no_network="${GPT_RUSTC_NO_NETWORK:-0}"
command_args=()

while (($# > 0)); do
  case "$1" in
    --project)
      (($# >= 2)) || fail '--project requires a directory'
      project_dir="$2"
      shift 2
      ;;
    --toolchain)
      (($# >= 2)) || fail '--toolchain requires a value'
      toolchain="$2"
      shift 2
      ;;
    --cache-dir)
      (($# >= 2)) || fail '--cache-dir requires a directory'
      cache_dir="$2"
      shift 2
      ;;
    --offline-bundle)
      (($# >= 2)) || fail '--offline-bundle requires a file'
      offline_bundle="$2"
      shift 2
      ;;
    --bundle-url)
      (($# >= 2)) || fail '--bundle-url requires a URL'
      bundle_url="$2"
      shift 2
      ;;
    --no-network)
      no_network=1
      shift
      ;;
    --force-managed)
      force_managed=1
      shift
      ;;
    --print-env)
      print_env=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      command_args=("$@")
      break
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

[[ -d "$project_dir" ]] || fail "project directory does not exist: $project_dir"
project_dir="$(cd "$project_dir" && pwd -P)"
mkdir -p "$cache_dir"
cache_dir="$(cd "$cache_dir" && pwd -P)"

sha256_file() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
  elif command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "$file" | awk '{print $NF}'
  else
    fail 'sha256sum, shasum, or openssl is required'
  fi
}

fetch() {
  local url="$1"
  local destination="$2"
  local temporary="$destination.tmp.$$"

  [[ "$no_network" != "1" ]] || fail "network access disabled; cannot fetch $url"
  rm -f "$temporary"
  if command -v curl >/dev/null 2>&1; then
    curl --proto '=https' --tlsv1.2 --fail --silent --show-error \
      --location "$url" --output "$temporary"
  elif command -v wget >/dev/null 2>&1; then
    wget --https-only --quiet "$url" --output-document="$temporary"
  else
    fail 'curl or wget is required for network bootstrap'
  fi
  mv "$temporary" "$destination"
}

host_target() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"

  case "$os:$arch" in
    Linux:x86_64|Linux:amd64) printf 'x86_64-unknown-linux-gnu' ;;
    Linux:aarch64|Linux:arm64) printf 'aarch64-unknown-linux-gnu' ;;
    Darwin:x86_64|Darwin:amd64) printf 'x86_64-apple-darwin' ;;
    Darwin:arm64|Darwin:aarch64) printf 'aarch64-apple-darwin' ;;
    *) fail "unsupported host: $os $arch" ;;
  esac
}

emit_or_run() {
  local source="$1"
  local rustc_bin="$2"
  local bin_dir
  bin_dir="$(cd "$(dirname "$rustc_bin")" && pwd -P)"
  export PATH="$bin_dir:$PATH"
  export GPT_RUSTC_SOURCE="$source"
  export GPT_RUSTC_BIN="$rustc_bin"

  local version
  version="$("$rustc_bin" --version)"
  log "compiler ready from $source: $version"

  if ((print_env == 1)); then
    printf 'export PATH=%q:$PATH\n' "$bin_dir"
    printf 'export GPT_RUSTC_SOURCE=%q\n' "$source"
    printf 'export GPT_RUSTC_BIN=%q\n' "$rustc_bin"
  fi

  if ((${#command_args[@]} > 0)); then
    command_name="${command_args[0]##*/}"
    command_flags="${command_args[1]:-}"
    if [[ "$command_name" == "bash" ]] &&        ([[ "$command_flags" == "--login" ]] || [[ "$command_flags" == -*l* ]]); then
      fail "refusing to launch a Bash login shell; it may replace PATH and hide the prepared compiler. Use 'bash -c' instead of 'bash -lc'."
    fi
    exec "${command_args[@]}"
  fi

  ((print_env == 1)) || printf '%s\n' "$version"
  exit 0
}

# Fastest path: a working compiler already exists.
if ((force_managed == 0)) && command -v rustc >/dev/null 2>&1; then
  existing_rustc="$(command -v rustc)"
  if "$existing_rustc" --version >/dev/null 2>&1; then
    log "reusing existing compiler: $existing_rustc"
    emit_or_run 'system' "$existing_rustc"
  fi
fi

host="$(host_target)"
toolchain_cache="$cache_dir/toolchains"
download_cache="$cache_dir/downloads"
mkdir -p "$toolchain_cache" "$download_cache"

# Reuse any previously extracted compatible bundle before touching the network.
while IFS= read -r candidate; do
  if [[ -x "$candidate/bin/rustc" ]] && "$candidate/bin/rustc" --version >/dev/null 2>&1; then
    emit_or_run 'offline-cache' "$candidate/bin/rustc"
  fi
done < <(find "$toolchain_cache" -mindepth 1 -maxdepth 1 -type d -name "*-$host" -print 2>/dev/null | sort -r)

verify_bundle() {
  local bundle="$1"
  local checksum_file="$bundle.sha256"
  [[ -f "$bundle" ]] || fail "offline bundle does not exist: $bundle"
  [[ -f "$checksum_file" ]] || fail "missing checksum sidecar: $checksum_file"

  local expected actual
  expected="$(awk 'NF {print $1; exit}' "$checksum_file")"
  actual="$(sha256_file "$bundle")"
  [[ "$expected" =~ ^[0-9a-fA-F]{64}$ ]] || fail 'invalid bundle checksum file'
  [[ "${actual,,}" == "${expected,,}" ]] || fail 'offline bundle SHA-256 mismatch'
}

extract_bundle() {
  local bundle="$1"
  verify_bundle "$bundle"

  local stem destination temporary extracted_root
  stem="$(basename "$bundle")"
  stem="${stem%.tar.zst}"
  stem="${stem%.tar.gz}"
  destination="$toolchain_cache/$stem"

  if [[ -x "$destination/bin/rustc" ]]; then
    emit_or_run 'offline-cache' "$destination/bin/rustc"
  fi

  temporary="$toolchain_cache/.extract-$stem-$$"
  rm -rf "$temporary"
  mkdir -p "$temporary"

  case "$bundle" in
    *.tar.zst)
      if tar --help 2>/dev/null | grep -q -- '--zstd'; then
        tar --zstd -xf "$bundle" -C "$temporary"
      elif command -v zstd >/dev/null 2>&1; then
        zstd -dc "$bundle" | tar -xf - -C "$temporary"
      else
        fail 'zstd support is required to extract the offline bundle'
      fi
      ;;
    *.tar.gz)
      tar -xzf "$bundle" -C "$temporary"
      ;;
    *)
      fail "unsupported offline bundle format: $bundle"
      ;;
  esac

  extracted_root="$(find "$temporary" -mindepth 1 -maxdepth 1 -type d -print -quit)"
  [[ -n "$extracted_root" && -x "$extracted_root/bin/rustc" ]] || \
    fail 'offline bundle does not contain a usable bin/rustc'

  rm -rf "$destination"
  mv "$extracted_root" "$destination"
  rm -rf "$temporary"
  emit_or_run 'offline-bundle' "$destination/bin/rustc"
}

# Explicit bundle wins over repository discovery.
if [[ -n "$offline_bundle" ]]; then
  extract_bundle "$(cd "$(dirname "$offline_bundle")" && pwd -P)/$(basename "$offline_bundle")"
fi

# An uploaded self-contained archive may place a toolchain under toolchains/.
shopt -s nullglob
repo_bundles=("$repo_root"/toolchains/rustc-lite-*"-$host".tar.zst "$repo_root"/toolchains/rustc-lite-*"-$host".tar.gz)
shopt -u nullglob
if ((${#repo_bundles[@]} > 0)); then
  extract_bundle "${repo_bundles[0]}"
fi

# Optional release asset URL. Its checksum is expected at URL.sha256.
if [[ -n "$bundle_url" ]]; then
  bundle_name="$(basename "${bundle_url%%\?*}")"
  [[ "$bundle_name" == *.tar.zst || "$bundle_name" == *.tar.gz ]] || \
    fail 'bundle URL must end in .tar.zst or .tar.gz'
  downloaded_bundle="$download_cache/$bundle_name"
  if [[ ! -f "$downloaded_bundle" ]]; then
    log "downloading offline Rust bundle: $bundle_url"
    fetch "$bundle_url" "$downloaded_bundle"
    fetch "$bundle_url.sha256" "$downloaded_bundle.sha256"
  fi
  extract_bundle "$downloaded_bundle"
fi

[[ "$no_network" != "1" ]] || \
  fail 'no usable system compiler, cached toolchain, or offline bundle was found'

resolve_project_toolchain() {
  local project="$1"
  local value=""
  if [[ -f "$project/rust-toolchain.toml" ]]; then
    value="$(sed -nE 's/^[[:space:]]*channel[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "$project/rust-toolchain.toml" | head -n 1)"
  elif [[ -f "$project/rust-toolchain" ]]; then
    value="$(sed -e 's/[[:space:]]*#.*$//' -e '/^[[:space:]]*$/d' "$project/rust-toolchain" | head -n 1 | tr -d '[:space:]')"
  fi
  printf '%s' "$value"
}

if [[ -z "$toolchain" ]]; then
  toolchain="$(resolve_project_toolchain "$project_dir")"
fi
[[ -n "$toolchain" ]] || toolchain='stable'
case "$toolchain" in
  *[!A-Za-z0-9._+-]*) fail "unsafe toolchain value: $toolchain" ;;
esac

rustup_home="$cache_dir/rustup"
cargo_home="$cache_dir/cargo"
bin_cache="$cache_dir/bin"
installer="$bin_cache/rustup-init-$host"
installer_checksum="$installer.sha256"
rustup_bin="$cargo_home/bin/rustup"
mkdir -p "$rustup_home" "$cargo_home" "$bin_cache"

if [[ ! -x "$installer" ]]; then
  base_url="https://static.rust-lang.org/rustup/dist/$host/rustup-init"
  log "downloading official rustup-init for $host"
  fetch "$base_url" "$installer"
  fetch "$base_url.sha256" "$installer_checksum"
  expected="$(awk 'NF {print $1; exit}' "$installer_checksum")"
  actual="$(sha256_file "$installer")"
  [[ "$expected" =~ ^[0-9a-fA-F]{64}$ ]] || fail 'invalid rustup-init checksum file'
  [[ "${actual,,}" == "${expected,,}" ]] || fail 'rustup-init SHA-256 mismatch'
  chmod 0755 "$installer"
fi

export RUSTUP_HOME="$rustup_home"
export CARGO_HOME="$cargo_home"
export PATH="$cargo_home/bin:$PATH"
export RUSTUP_TOOLCHAIN="$toolchain"

if [[ ! -x "$rustup_bin" ]]; then
  log "installing toolchain '$toolchain' with minimal profile"
  "$installer" -y --no-modify-path --profile minimal --default-toolchain "$toolchain"
elif "$rustup_bin" run "$toolchain" rustc --version >/dev/null 2>&1; then
  log "reusing cached toolchain '$toolchain' through rustup"
else
  log "installing missing rustup toolchain '$toolchain'"
  "$rustup_bin" toolchain install "$toolchain" --profile minimal
fi

emit_or_run 'rustup-cache' "$cargo_home/bin/rustc"
