#!/usr/bin/env bash
set -euo pipefail

repo="${1:?usage: bash apply.sh /path/to/repository}"
pack_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -s "$pack_dir/patch/delete-paths.txt" ]]; then
  while IFS= read -r path; do
    [[ -z "$path" || "$path" == \#* ]] && continue
    rm -rf -- "$repo/$path"
  done < "$pack_dir/patch/delete-paths.txt"
fi

if [[ -s "$pack_dir/patch/changes.patch" ]]; then
  git -C "$repo" apply --index "$pack_dir/patch/changes.patch"
fi

if [[ -d "$pack_dir/overlay" ]]; then
  cp -a "$pack_dir/overlay/." "$repo/"
fi
