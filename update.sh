#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash update.sh --project PATH --version REF [options]

Options:
  --project PATH       Target project repository. Required.
  --version REF        New workflow tag or ref. Required.
  --execution-mode MODE  gpt_tunnel_managed or repository_evidence. Required.
  --repository URL     Override repository from existing lock file.
  --commit SHA         Exact commit. Otherwise resolved with git ls-remote.
  --release-publication-file PATH
                       Existing explicit project publication declaration.
  --agents-file PATH   AGENTS.md path relative to project. Default: AGENTS.md
  -h, --help           Show this help.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

project=""
version=""
repository=""
commit=""
execution_mode=""
agents_file="AGENTS.md"
release_publication_file=""

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
[[ -n "$version" ]] || die "--version is required"
[[ "$execution_mode" == "gpt_tunnel_managed" || "$execution_mode" == "repository_evidence" ]] ||
  die "--execution-mode must be gpt_tunnel_managed or repository_evidence"
[[ -d "$project" ]] || die "project directory does not exist: $project"

project="$(cd "$project" && pwd)"
lock_file="$project/.gpt-workflow.lock"
[[ -f "$lock_file" ]] || die "missing $lock_file; run setup.sh first"

if [[ -z "$repository" ]]; then
  repository="$(
    sed -n 's/^[[:space:]]*"repository"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
      "$lock_file" | head -n 1
  )"
fi

[[ -n "$repository" ]] || die "unable to read repository from $lock_file"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
args=(
  --project "$project"
  --version "$version"
  --repository "$repository"
  --execution-mode "$execution_mode"
  --agents-file "$agents_file"
  --force
  --release-publication-file "${release_publication_file:-$project/release-publication.json}"
)

if [[ -n "$commit" ]]; then
  args+=(--commit "$commit")
fi

exec bash "$script_dir/setup.sh" "${args[@]}"
