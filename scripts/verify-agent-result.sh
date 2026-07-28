#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
usage:
  verify-agent-result.sh prepare REPOSITORY IMPLEMENTATION_SHA
  verify-agent-result.sh committed REPOSITORY IMPLEMENTATION_SHA [EVIDENCE_SHA]
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

mode="${1:-}"
[[ -n "$mode" ]] || { usage >&2; exit 2; }
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
  *) usage >&2; exit 2 ;;
esac
