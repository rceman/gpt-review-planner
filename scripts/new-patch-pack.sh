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
EOF
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
source_dir="$repo_root/templates/executable-patch-pack"

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
    --baseline-release) baseline_release="${2:?missing value}"; shift 2 ;;
    --slug) patch_slug="${2:?missing value}"; shift 2 ;;
    --title) title="${2:?missing value}"; shift 2 ;;
    --description) description="${2:?missing value}"; shift 2 ;;
    --target-repository) target_repository="${2:?missing value}"; shift 2 ;;
    --target-branch) target_branch="${2:?missing value}"; shift 2 ;;
    --base-revision) base_revision="${2:?missing value}"; shift 2 ;;
    --output) output_root="${2:?missing value}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

[[ "$baseline_release" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([+-][0-9A-Za-z.-]+)?$ ]] || { echo "invalid --baseline-release" >&2; exit 2; }
[[ "$patch_slug" =~ ^[a-z0-9]+(-[a-z0-9]+){0,2}$ ]] || { echo "invalid --slug" >&2; exit 2; }
[[ -n "$title" && -n "$description" && -n "$target_repository" && -n "$target_branch" && -n "$output_root" ]] || { usage; exit 2; }
[[ "$base_revision" =~ ^[0-9a-f]{40}$ ]] || { echo "--base-revision must be a lowercase 40-character Git SHA" >&2; exit 2; }
word_count="$(printf '%s' "$title" | awk '{print NF}')"
[[ "$word_count" -ge 2 && "$word_count" -le 6 && "${#title}" -le 80 ]] || { echo "invalid --title" >&2; exit 2; }
[[ "${#description}" -le 240 && "$description" == *[.!?] ]] || { echo "invalid --description" >&2; exit 2; }

now="$(date -u +%Y%m%d-%H%M%S:%Y-%m-%dT%H:%M:%SZ)"
patch_timestamp="${now%%:*}"
created_at="${now#*:}"
patch_id="patch-${patch_timestamp}-${patch_slug}"
destination="$output_root/$patch_id"
[[ ! -e "$destination" ]] || { echo "destination already exists: $destination" >&2; exit 1; }

workflow_version="v$(tr -d '\r\n' < "$repo_root/VERSION")"
workflow_commit="$(git -C "$repo_root" rev-parse HEAD^{commit})"
evidence_directory=".gpt-review/evidence/${baseline_release}/${patch_id}"

mkdir -p "$output_root"
cp -a "$source_dir" "$destination"
touch "$destination/evidence.json"
for tool in patch_pack_scope.py verify-agent-evidence.py verify-agent-result.sh; do
  cp "$repo_root/scripts/$tool" "$destination/scripts/$tool"
done
chmod +x "$destination/scripts/"*

python3 - "$destination" "$patch_id" "$baseline_release" "$patch_slug" "$patch_timestamp" "$created_at" "$title" "$description" "$target_repository" "$target_branch" "$base_revision" "$evidence_directory" "$workflow_version" "$workflow_commit" <<'PY'
from pathlib import Path
import json
import sys

(root_arg, patch_id, baseline, slug, timestamp, created_at, title, description,
 repository, branch, base, evidence_dir, workflow_version, workflow_commit) = sys.argv[1:]
root = Path(root_arg)
manifest_path = root / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest.update({
    "patch_id": patch_id,
    "title": title,
    "description": description,
    "created_at": created_at,
    "patch_timestamp": timestamp,
    "patch_slug": slug,
    "baseline_release": baseline,
    "evidence_directory": evidence_dir,
})
manifest["workflow"] = {
    "repository": "https://github.com/rceman/gpt-review-planner",
    "version": workflow_version,
    "commit": workflow_commit,
    "document": "GPT_REVIEW_PLANNER.md",
}
manifest["target"] = {"repository": repository, "branch": branch, "base_revision": base}
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

handoff_path = root / "AGENT_HANDOFF.md"
handoff = handoff_path.read_text(encoding="utf-8")
values = {
    "TEMPLATE_PATCH_ID": patch_id,
    "TEMPLATE_WORKFLOW_REPOSITORY": manifest["workflow"]["repository"],
    "TEMPLATE_WORKFLOW_VERSION": workflow_version,
    "TEMPLATE_WORKFLOW_COMMIT": workflow_commit,
    "TEMPLATE_WORKFLOW_DOCUMENT": manifest["workflow"]["document"],
    "TEMPLATE_TARGET_REPOSITORY": repository,
    "TEMPLATE_TARGET_BRANCH": branch,
    "TEMPLATE_BASE_REVISION": base,
    "TEMPLATE_EVIDENCE_DIRECTORY": evidence_dir,
}
for old, new in values.items():
    handoff = handoff.replace(old, new)
handoff_path.write_text(handoff, encoding="utf-8")
PY

cp "$destination/AGENT_HANDOFF.md" "$destination/AGENT_PROMPT.md"
cat <<EOF
Created template-state patch pack: $destination
It is intentionally not ready for delivery until requirements, gates, evidence IDs, and implementation payload are complete.
Ready-state validation commands:
  python3 "$repo_root/scripts/validate-patch-pack.py" "$destination"
  python3 "$repo_root/scripts/validate-patch-pack.py" --format json "$destination"
EOF
