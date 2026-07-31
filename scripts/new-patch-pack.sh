#!/usr/bin/env bash
set -euo pipefail
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/build-gpt-patch-pack-v2.py" "$@"
