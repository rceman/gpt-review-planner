#!/usr/bin/env bash
set -euo pipefail

CANONICAL_REPOSITORY="https://github.com/rceman/gpt-review-planner"
DOCUMENT_PATH="GPT_REVIEW_PLANNER.md"
ARCHIVE_REVIEW_PROMPT_PATH="prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md"
ARCHIVE_REVIEW_ONLY_PROMPT_PATH="prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md"
ARCHIVE_PREP_PROMPT_PATH="prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md"
ARCHIVE_GUIDE_PATH="docs/PROJECT_ARCHIVE_REVIEW.md"
RELEASE_PROCESS_PATH="docs/RELEASE_PROCESS.md"
RELEASE_LIFECYCLE_PATH="docs/RELEASE_LIFECYCLE.md"
BLOCK_BEGIN="<!-- BEGIN GPT-REVIEW-PLANNER -->"
BLOCK_END="<!-- END GPT-REVIEW-PLANNER -->"

usage() {
  cat <<'EOF'
Usage:
  bash setup.sh --project PATH [options]

Options:
  --project PATH       Target project repository. Required.
  --version REF        Workflow tag or ref. Required.
  --execution-mode MODE  gpt_tunnel_managed or repository_evidence. Required.
  --repository URL     Canonical repository URL.
  --commit SHA         Exact commit. Otherwise resolved with git ls-remote.
  --release-publication-file PATH
                       Explicit project release-publication.json to validate and install.
  --agents-file PATH   AGENTS.md path relative to project. Default: AGENTS.md
  --force              Replace an existing lock even if repository differs.
  -h, --help           Show this help.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

resolve_commit() {
  local repository="$1"
  local version="$2"
  local resolved

  command -v git >/dev/null 2>&1 || die "git is required to resolve the workflow commit"

  resolved="$(
    git ls-remote "$repository" "refs/tags/${version}^{}" |
    awk 'NR == 1 { print $1 }'
  )"

  if [[ -z "$resolved" ]]; then
    resolved="$(
      git ls-remote "$repository" \
        "refs/tags/${version}" \
        "refs/heads/${version}" \
        "$version" |
      awk 'NR == 1 { print $1 }'
    )"
  fi

  [[ -n "$resolved" ]] || die "unable to resolve '$version' in '$repository'"
  printf '%s\n' "$resolved"
}

validate_managed_block() {
  local source_file="$1"
  local begin_count
  local end_count

  begin_count="$(grep -Fxc "$BLOCK_BEGIN" "$source_file" || true)"
  end_count="$(grep -Fxc "$BLOCK_END" "$source_file" || true)"

  if [[ "$begin_count" -ne "$end_count" || "$begin_count" -gt 1 ]]; then
    die "AGENTS.md contains malformed or duplicate GPT Review Planner markers"
  fi
}

remove_managed_block() {
  local source_file="$1"
  local destination_file="$2"

  awk -v begin="$BLOCK_BEGIN" -v end="$BLOCK_END" '
    $0 == begin { in_block = 1; next }
    $0 == end   { in_block = 0; next }
    !in_block   { print }
  ' "$source_file" > "$destination_file"
}

render_block() {
  local repository="$1"
  local version="$2"
  local commit="$3"
  local lock_link="$4"
  local execution_mode="$5"
  local browser_repository="${repository%.git}"

  cat <<EOF
${BLOCK_BEGIN}
> [!IMPORTANT]
> Before substantial planning, implementation, review, or correction work,
> load the external workflow pinned by [\`.gpt-workflow.lock\`](${lock_link}).
>
> Canonical repository: [\`${repository}\`](${browser_repository})
>
> Pinned workflow document:
> [\`${DOCUMENT_PATH}\`](${browser_repository}/blob/${commit}/${DOCUMENT_PATH})
>
> Pinned workflow: \`${version}\` at commit \`${commit}\`
> Execution mode: \`${execution_mode}\` (explicit; no autodetection or fallback)
>
> Attached code-project reviews default to:
> [\`${ARCHIVE_REVIEW_PROMPT_PATH}\`](${browser_repository}/blob/${commit}/${ARCHIVE_REVIEW_PROMPT_PATH})
> Review-only mode is used only when explicitly requested:
> [\`${ARCHIVE_REVIEW_ONLY_PROMPT_PATH}\`](${browser_repository}/blob/${commit}/${ARCHIVE_REVIEW_ONLY_PROMPT_PATH})
> Archive preparation uses the pinned official tooling and prompt:
> [\`${ARCHIVE_PREP_PROMPT_PATH}\`](${browser_repository}/blob/${commit}/${ARCHIVE_PREP_PROMPT_PATH})
> Archive guide: [\`${ARCHIVE_GUIDE_PATH}\`](${browser_repository}/blob/${commit}/${ARCHIVE_GUIDE_PATH})
> Release process: [\`${RELEASE_PROCESS_PATH}\`](${browser_repository}/blob/${commit}/${RELEASE_PROCESS_PATH})
> Release lifecycle: [\`${RELEASE_LIFECYCLE_PATH}\`](${browser_repository}/blob/${commit}/${RELEASE_LIFECYCLE_PATH})
>
> If \`engineering-profile.json\` is present, validate it with the exact pinned
> planner checkout and follow the selected profile and relevant documents.
> Owner instructions win; apply exceptions narrowly and report policy conflicts
> instead of silently selecting another stack. Prefer Rust/Axum for new backend
> components; use Go/Gin only when selected or approved. Production Node.js
> backends and direct frontend database access are forbidden. PostgreSQL schema
> authority remains Liquibase. Python rules apply to tools/tests; a valid legacy
> Python exception does not demand rewrite.
>
> Any release, version bump, or version-tag request requires reading the exact commit-pinned release lifecycle and release process.
> The owner explicitly selects the target version.
> Only repository release automation may modify synchronized version files; manual version synchronization is forbidden.
> Release-surface tasks declare exactly one lifecycle mode and target version in the task-specific handoff. Use `check-source` for `implementation_unreleased`; use the ordered prepare/check-release-ready/commit/check-tag-ready/tag/verify-tag flow for `release_publication`. A source-state pass is not release or tag readiness.
> Operating model:
> - GPT owns architecture, behavior contracts, fixtures, tests, review, and the principal implementation.
> - The local agent owns integration, dependency restoration, compilation, runtime tests, and minimal integration corrections.
> - The local agent must not redesign approved behavior or weaken tests and acceptance criteria.
> - Do not hand-author \`.gpt-workflow.lock\`; use the pinned preparation prompt and official setup/update tooling.
> - GPT performs only static validation and does not execute runtime quality gates. GPT still authors the approved implementation, fixtures, and tests.
> - The local agent owns runtime integration and gates.
> - Release-commit CI must pass before tagging; final tag CI is external metadata.
> - Never force-push or use broad \`git push --tags\`.
> - Before release task authoring, load and validate the explicit project declaration with \`python3 scripts/validate-release-publication.py release-publication.json --repo .\`.
> - After \`git push origin refs/tags/v<TARGET_VERSION>:refs/tags/v<TARGET_VERSION>\`, derive the post-tag proof from that declaration: \`none\` has no publication task, \`tag_only\` verifies declared tag CI, and \`github_actions\` verifies the declared publication workflow plus GitHub Release/assets when expected.
> - Owner authorization to push the exact tag includes only declaration-authorized automatic workflow side effects; it does not authorize manual API/CLI publication, installation, activation, restart, or connector refresh.
> - Local \`gh\`, curl, wget, \`GH_TOKEN\`, and \`GITHUB_TOKEN\` publication is forbidden.
${BLOCK_END}
EOF
}

project=""
version=""
repository="$CANONICAL_REPOSITORY"
commit=""
execution_mode=""
agents_file="AGENTS.md"
release_publication_file=""
force=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      [[ $# -ge 2 ]] || die "--project requires a value"
      project="$2"
      shift 2
      ;;
    --version)
      [[ $# -ge 2 ]] || die "--version requires a value"
      version="$2"
      shift 2
      ;;
    --repository)
      [[ $# -ge 2 ]] || die "--repository requires a value"
      repository="$2"
      shift 2
      ;;
    --commit)
      [[ $# -ge 2 ]] || die "--commit requires a value"
      commit="$2"
      shift 2
      ;;
    --release-publication-file)
      [[ $# -ge 2 ]] || die "--release-publication-file requires a value"
      release_publication_file="$2"
      shift 2
      ;;
    --execution-mode)
      [[ $# -ge 2 ]] || die "--execution-mode requires a value"
      execution_mode="$2"
      shift 2
      ;;
    --agents-file)
      [[ $# -ge 2 ]] || die "--agents-file requires a value"
      agents_file="$2"
      shift 2
      ;;
    --force)
      force=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -n "$version" ]] || die "--version is required"
[[ "$execution_mode" == "gpt_tunnel_managed" || "$execution_mode" == "repository_evidence" ]] ||
  die "--execution-mode must be gpt_tunnel_managed or repository_evidence"

[[ -n "$project" ]] || die "--project is required"
[[ -d "$project" ]] || die "project directory does not exist: $project"

project="$(cd "$project" && pwd)"
planner_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[[ -n "$release_publication_file" ]] || die "--release-publication-file is required; no publication mode is inferred"
if [[ "$release_publication_file" != /* ]]; then
  release_publication_file="$(cd "$(dirname "$release_publication_file")" && pwd)/$(basename "$release_publication_file")"
fi
[[ -f "$release_publication_file" && ! -L "$release_publication_file" ]] ||
  die "release-publication input must be a regular non-symlink file"
python3 "$planner_root/scripts/validate-release-publication.py" \
  "$release_publication_file" --repo "$project" >/dev/null ||
  die "release-publication input failed canonical validation"

[[ "$agents_file" != /* ]] || die "--agents-file must be relative to the project"
[[ "$agents_file" != ".." && "$agents_file" != ../* && "$agents_file" != *"/../"* ]] ||
  die "--agents-file must not escape the project"

lock_file="$project/.gpt-workflow.lock"
agents_path="$project/$agents_file"
agents_dir="$(dirname "$agents_file")"

if [[ "$agents_dir" == "." ]]; then
  lock_link="./.gpt-workflow.lock"
else
  lock_link=""
  IFS='/' read -r -a agents_dir_parts <<< "$agents_dir"
  for _part in "${agents_dir_parts[@]}"; do
    [[ -n "$_part" && "$_part" != "." ]] && lock_link+="../"
  done
  lock_link+=".gpt-workflow.lock"
fi

if [[ -f "$lock_file" && "$force" -ne 1 ]]; then
  existing_repository="$(
    sed -n 's/^[[:space:]]*"repository"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
      "$lock_file" | head -n 1
  )"
  if [[ -n "$existing_repository" && "$existing_repository" != "$repository" ]]; then
    die "existing lock points to '$existing_repository'; use --force to replace it"
  fi
fi

if [[ -z "$commit" ]]; then
  commit="$(resolve_commit "$repository" "$version")"
fi

[[ "$commit" =~ ^[0-9a-fA-F]{40}$ ]] || die "commit must be a 40-character Git SHA"

mkdir -p "$(dirname "$agents_path")"
tmp_clean="$(mktemp)"
tmp_agents="$(mktemp)"
trap 'rm -f "$tmp_clean" "$tmp_agents"' EXIT

if [[ -f "$agents_path" ]]; then
  validate_managed_block "$agents_path"
  remove_managed_block "$agents_path" "$tmp_clean"
else
  : > "$tmp_clean"
fi

{
  render_block "$repository" "$version" "$commit" "$lock_link" "$execution_mode"
  printf '\n'
  awk '
    BEGIN { started = 0 }
    {
      if (!started && $0 ~ /^[[:space:]]*$/) next
      started = 1
      print
    }
  ' "$tmp_clean"
} > "$tmp_agents"

mv "$tmp_agents" "$agents_path"

generated_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
cat > "$lock_file" <<EOF
{
  "schema_version": 2,
  "repository": "${repository}",
  "version": "${version}",
  "commit": "${commit}",
  "document": "${DOCUMENT_PATH}",
  "execution_mode": "${execution_mode}",
  "installed_at": "${generated_at}"
}
EOF

publication_declaration="$project/release-publication.json"
if [[ "$release_publication_file" != "$publication_declaration" ]]; then
  cp "$release_publication_file" "$publication_declaration"
fi

printf 'Installed GPT Review Planner integration.\n'
printf 'Project: %s\n' "$project"
printf 'AGENTS: %s\n' "$agents_path"
printf 'Lock: %s\n' "$lock_file"
printf 'Workflow: %s @ %s\n' "$version" "$commit"
