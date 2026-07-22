#!/usr/bin/env bash
set -euo pipefail

pack_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -d "$pack_dir/reference/python" ]]; then
  python -m unittest discover -s "$pack_dir/reference/python" -v
fi
