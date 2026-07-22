#!/usr/bin/env bash
set -euo pipefail

patch_id="${1:?usage: bash scripts/new-patch-pack.sh PATCH_ID OUTPUT_DIRECTORY}"
output_root="${2:?usage: bash scripts/new-patch-pack.sh PATCH_ID OUTPUT_DIRECTORY}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
source_dir="$repo_root/templates/executable-patch-pack"
destination="$output_root/$patch_id"

[[ ! -e "$destination" ]] || {
  echo "destination already exists: $destination" >&2
  exit 1
}

mkdir -p "$output_root"
cp -a "$source_dir" "$destination"

python - "$destination" "$patch_id" <<'PY'
from pathlib import Path
import json
import sys

root = Path(sys.argv[1])
patch_id = sys.argv[2]

for path in root.rglob("*"):
    if not path.is_file():
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    path.write_text(text.replace("REPLACE_PATCH_ID", patch_id), encoding="utf-8")

manifest_path = root / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["patch_id"] = patch_id
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY

echo "Created $destination"
