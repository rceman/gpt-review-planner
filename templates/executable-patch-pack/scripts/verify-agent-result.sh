#!/usr/bin/env bash
set -euo pipefail

repo="${1:?usage: bash verify-agent-result.sh /path/to/repository}"

git -C "$repo" diff --check
git -C "$repo" status --short
