#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage:
  bash scripts/new-patch-pack.sh \
    --baseline-release vX.Y.Z \
    --slug one-to-three-words \
    --title "Two to six words" \
    --description "One short sentence." \
    --target-repository owner/repository \
    --target-branch branch-name \
    --base-revision 40_CHARACTER_GIT_SHA \
    --output OUTPUT_DIRECTORY

legacy compatibility:
  bash scripts/new-patch-pack.sh PATCH_ID OUTPUT_DIRECTORY
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
source_dir="$repo_root/templates/executable-patch-pack"

legacy=false
if [[ $# -eq 2 && "${1:-}" != --* ]]; then
  legacy=true
  patch_id="$1"
  output_root="$2"
  baseline_release="REPLACE_BASELINE_RELEASE"
  patch_slug="REPLACE_PATCH_SLUG"
  now="$(date -u +%Y%m%d-%H%M%S:%Y-%m-%dT%H:%M:%SZ)"
  patch_timestamp="${now%%:*}"
  created_at="${now#*:}"
  title="REPLACE_TITLE"
  description="REPLACE_DESCRIPTION"
  target_repository="REPLACE_REPOSITORY"
  target_branch="REPLACE_BRANCH"
  base_revision="REPLACE_BASE_REVISION"
else
  baseline_release=""
  patch_slug=""
  title=""
  description=""
  target_repository=""
  target_branch=""
  base_revision=""
  output_root=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --baseline-release) baseline_release="${2:?missing value for --baseline-release}"; shift 2 ;;
      --slug) patch_slug="${2:?missing value for --slug}"; shift 2 ;;
      --title) title="${2:?missing value for --title}"; shift 2 ;;
      --description) description="${2:?missing value for --description}"; shift 2 ;;
      --target-repository) target_repository="${2:?missing value for --target-repository}"; shift 2 ;;
      --target-branch) target_branch="${2:?missing value for --target-branch}"; shift 2 ;;
      --base-revision) base_revision="${2:?missing value for --base-revision}"; shift 2 ;;
      --output) output_root="${2:?missing value for --output}"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
    esac
  done

  [[ "$baseline_release" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([+-][0-9A-Za-z.-]+)?$ ]] || {
    echo "--baseline-release must be a v-prefixed semantic version" >&2; exit 2;
  }
  [[ "$patch_slug" =~ ^[a-z0-9]+(-[a-z0-9]+){0,2}$ ]] || {
    echo "--slug must contain one to three lowercase kebab-case words" >&2; exit 2;
  }
  [[ -n "$title" && -n "$description" && -n "$target_repository" && -n "$target_branch" && -n "$output_root" ]] || {
    echo "all canonical arguments are required" >&2; usage; exit 2;
  }
  title_word_count="$(printf '%s' "$title" | awk '{print NF}')"
  [[ "$title_word_count" -ge 2 && "$title_word_count" -le 6 && "${#title}" -le 80 && "$title" != *$'\n'* ]] || {
    echo "--title must contain 2-6 words, no newline, and at most 80 characters" >&2; exit 2;
  }
  [[ "${#description}" -le 240 && "$description" != *$'\n'* && "$description" == *[.!?] ]] || {
    echo "--description must be one line, at most 240 characters, ending in punctuation" >&2; exit 2;
  }
  [[ "$base_revision" =~ ^[0-9a-fA-F]{40}$ ]] || {
    echo "--base-revision must be a 40-character Git SHA" >&2; exit 2;
  }
  now="$(date -u +%Y%m%d-%H%M%S:%Y-%m-%dT%H:%M:%SZ)"
  patch_timestamp="${now%%:*}"
  created_at="${now#*:}"
  patch_id="patch-${patch_timestamp}-${patch_slug}"
fi

destination="$output_root/$patch_id"
[[ ! -e "$destination" ]] || { echo "destination already exists: $destination" >&2; exit 1; }

workflow_version="v$(tr -d '\r\n' < "$repo_root/VERSION")"
workflow_commit="$(git -C "$repo_root" rev-parse HEAD)"
evidence_directory=".gpt-review/evidence/${baseline_release}/${patch_id}"

mkdir -p "$output_root"
cp -a "$source_dir" "$destination"
cp "$repo_root/scripts/patch_pack_scope.py" "$destination/scripts/patch_pack_scope.py"
cp "$repo_root/scripts/verify-agent-evidence.py" "$destination/scripts/verify-agent-evidence.py"
chmod +x "$destination/scripts/patch_pack_scope.py" "$destination/scripts/verify-agent-evidence.py"

python3 - \
  "$destination" \
  "$patch_id" \
  "$baseline_release" \
  "$patch_slug" \
  "$patch_timestamp" \
  "$created_at" \
  "$title" \
  "$description" \
  "$target_repository" \
  "$target_branch" \
  "$base_revision" \
  "$evidence_directory" \
  "$workflow_version" \
  "$workflow_commit" <<'PY'
from pathlib import Path
import json
import sys

(
    destination,
    patch_id,
    baseline_release,
    patch_slug,
    patch_timestamp,
    created_at,
    title,
    description,
    target_repository,
    target_branch,
    base_revision,
    evidence_directory,
    workflow_version,
    workflow_commit,
) = sys.argv[1:]
root = Path(destination)
values = {
    "REPLACE_PATCH_ID": patch_id,
    "REPLACE_BASELINE_RELEASE": baseline_release,
    "REPLACE_PATCH_SLUG": patch_slug,
    "REPLACE_PATCH_TIMESTAMP": patch_timestamp,
    "REPLACE_CREATED_AT": created_at,
    "REPLACE_TITLE": title,
    "REPLACE_DESCRIPTION": description,
    "REPLACE_REPOSITORY": target_repository,
    "REPLACE_BRANCH": target_branch,
    "REPLACE_BASE_REVISION": base_revision,
    "REPLACE_EVIDENCE_DIRECTORY": evidence_directory,
    "REPLACE_WORKFLOW_VERSION": workflow_version,
    "REPLACE_WITH_40_CHARACTER_COMMIT_SHA": workflow_commit,
}
for path in root.rglob("*"):
    if not path.is_file():
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for old, new in values.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")

manifest_path = root / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

if $legacy; then
  echo "Created legacy-compatible pack $destination; fill all REPLACE fields before validation." >&2
else
  echo "Created $destination"
fi
