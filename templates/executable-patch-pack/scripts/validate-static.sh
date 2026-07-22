#!/usr/bin/env bash
set -euo pipefail

repo="${1:?usage: bash validate-static.sh /path/to/repository}"

git -C "$repo" diff --check

if find "$repo" -type f \( -name '*Zone.Identifier*' -o -name '*Zone.Identifier' \) -print -quit | grep -q .; then
  echo "forbidden Zone.Identifier files found" >&2
  exit 1
fi
