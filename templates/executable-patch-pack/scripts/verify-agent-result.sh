#!/usr/bin/env bash
set -euo pipefail

repo="${1:?usage: bash verify-agent-result.sh /path/to/repository}"
pack_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

python3 "$pack_dir/scripts/patch_pack_scope.py" verify-result "$pack_dir" "$repo"
git -C "$repo" status --short
