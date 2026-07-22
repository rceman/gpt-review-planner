#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash update.sh --project PATH --version REF [options]

Options:
  --project PATH       Target project repository. Required.
  --version REF        New workflow tag or ref. Required.
  --repository URL     Override repository from existing lock file.
  --commit SHA         Exact commit. Otherwise resolved with git ls-remote.
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
agents_file="AGENTS.md"

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
  --agents-file "$agents_file"
  --force
)

if [[ -n "$commit" ]]; then
  args+=(--commit "$commit")
fi

exec bash "$script_dir/setup.sh" "${args[@]}"
