#!/usr/bin/env bash
set -euo pipefail

CANONICAL_REPOSITORY="https://github.com/rceman/gpt-review-planner"
DEFAULT_VERSION="v1.0.0"
DOCUMENT_PATH="GPT_REVIEW_PLANNER.md"
BLOCK_BEGIN="<!-- BEGIN GPT-REVIEW-PLANNER -->"
BLOCK_END="<!-- END GPT-REVIEW-PLANNER -->"

usage() {
  cat <<'EOF'
Usage:
  bash setup.sh --project PATH [options]

Options:
  --project PATH       Target project repository. Required.
  --version REF        Workflow tag or ref. Default: v1.0.0
  --repository URL     Canonical repository URL.
  --commit SHA         Exact commit. Otherwise resolved with git ls-remote.
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
>
> Operating model:
> - GPT owns architecture, behavior contracts, fixtures, tests, review, and the principal implementation.
> - The local agent owns integration, dependency restoration, compilation, runtime tests, and minimal integration corrections.
> - The local agent must not redesign approved behavior or weaken tests and acceptance criteria.
${BLOCK_END}
EOF
}

project=""
version="$DEFAULT_VERSION"
repository="$CANONICAL_REPOSITORY"
commit=""
agents_file="AGENTS.md"
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

[[ -n "$project" ]] || die "--project is required"
[[ -d "$project" ]] || die "project directory does not exist: $project"

project="$(cd "$project" && pwd)"

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
  render_block "$repository" "$version" "$commit" "$lock_link"
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
  "schema_version": 1,
  "repository": "${repository}",
  "version": "${version}",
  "commit": "${commit}",
  "document": "${DOCUMENT_PATH}",
  "installed_at": "${generated_at}"
}
EOF

printf 'Installed GPT Review Planner integration.\n'
printf 'Project: %s\n' "$project"
printf 'AGENTS: %s\n' "$agents_path"
printf 'Lock: %s\n' "$lock_file"
printf 'Workflow: %s @ %s\n' "$version" "$commit"
