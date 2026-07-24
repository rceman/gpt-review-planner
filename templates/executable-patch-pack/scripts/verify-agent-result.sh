#!/usr/bin/env bash
set -euo pipefail

mode="${1:?usage: verify-agent-result.sh prepare|committed REPOSITORY IMPLEMENTATION_SHA [EVIDENCE_SHA]}"
repo="${2:?missing repository}"
implementation="${3:?missing implementation SHA}"
evidence="${4:-HEAD}"
pack_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

case "$mode" in
  prepare)
    python3 "$pack_dir/scripts/verify-agent-evidence.py" prepare \
      --pack "$pack_dir" \
      --repo "$repo" \
      --implementation-commit "$implementation"
    ;;
  committed)
    python3 "$pack_dir/scripts/verify-agent-evidence.py" committed \
      --pack "$pack_dir" \
      --repo "$repo" \
      --implementation-commit "$implementation" \
      --evidence-commit "$evidence"
    ;;
  *) echo "mode must be prepare or committed" >&2; exit 2 ;;
esac
