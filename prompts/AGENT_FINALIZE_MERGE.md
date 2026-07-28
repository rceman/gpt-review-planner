# Agent Merge Finalization

Load the exact pinned `docs/PROCEDURE_INDEX.md`, `docs/AGENT_REPORTING.md`, and
`docs/POST_MERGE_BRANCH_CLEANUP.md` before execution. Substitute all parameters
from the owner handoff; do not infer identities from HEAD.

```bash
set -euo pipefail
REPOSITORY="<REPOSITORY>"
LOCAL_REPOSITORY="<LOCAL_REPOSITORY>"
SSH_ORIGIN="<SSH_ORIGIN>"
MAIN_BRANCH="<MAIN_BRANCH>"
FEATURE_BRANCH="<FEATURE_BRANCH>"
EXPECTED_MAIN_BEFORE="<EXPECTED_MAIN_BEFORE>"
EXPECTED_FEATURE_HEAD="<EXPECTED_FEATURE_HEAD>"
EXPECTED_VERSION="<EXPECTED_VERSION>"
CI_POLICY="<CI_POLICY>"
CI_WORKFLOW="<CI_WORKFLOW>"
CI_EVENT="<CI_EVENT>"

REMOTE_MAIN_REF="refs/remotes/origin/${MAIN_BRANCH}"
REMOTE_FEATURE_REF="refs/remotes/origin/${FEATURE_BRANCH}"
LOCAL_MAIN_REF="refs/heads/${MAIN_BRANCH}"
LOCAL_FEATURE_REF="refs/heads/${FEATURE_BRANCH}"

cd "${LOCAL_REPOSITORY}"
git fetch origin --prune --tags
test "$(git remote get-url origin)" = "${SSH_ORIGIN}"
test -z "$(git status --porcelain)"
test "$(git rev-parse --verify "${REMOTE_MAIN_REF}^{commit}")" = "${EXPECTED_MAIN_BEFORE}"
test "$(git rev-parse --verify "${REMOTE_FEATURE_REF}^{commit}")" = "${EXPECTED_FEATURE_HEAD}"
test "$(git rev-parse --verify "${LOCAL_MAIN_REF}^{commit}")" = "${EXPECTED_MAIN_BEFORE}"
test "$(git rev-parse --verify "${LOCAL_FEATURE_REF}^{commit}")" = "${EXPECTED_FEATURE_HEAD}"
test "$(cat VERSION)" = "${EXPECTED_VERSION}"
git merge-base --is-ancestor "${REMOTE_MAIN_REF}" "${REMOTE_FEATURE_REF}"

git switch "${MAIN_BRANCH}"
git merge --no-ff --no-edit "${LOCAL_FEATURE_REF}" || { git merge --abort || true; echo MERGE_BLOCKED; exit 1; }
MERGE_SHA="$(git rev-parse HEAD)"
read -r ACTUAL PARENT_ONE PARENT_TWO EXTRA <<EOF
$(git rev-list --parents -n 1 "${MERGE_SHA}")
EOF
test "${ACTUAL}" = "${MERGE_SHA}"
test "${PARENT_ONE}" = "${EXPECTED_MAIN_BEFORE}"
test "${PARENT_TWO}" = "${EXPECTED_FEATURE_HEAD}"
test -z "${EXTRA:-}"
git merge-base --is-ancestor "${EXPECTED_FEATURE_HEAD}" "${MERGE_SHA}"
git diff --quiet "${EXPECTED_FEATURE_HEAD}" "${MERGE_SHA}" --
test "$(cat VERSION)" = "${EXPECTED_VERSION}"
test -z "$(git status --porcelain)"

git push origin "refs/heads/${MAIN_BRANCH}:refs/heads/${MAIN_BRANCH}"
git fetch origin --prune
test "$(git rev-parse --verify "${REMOTE_MAIN_REF}^{commit}")" = "${MERGE_SHA}"

python3 scripts/check-github-ci.py \
  --repository "${REPOSITORY}" --sha "${MERGE_SHA}" --policy "${CI_POLICY}" \
  --workflow "${CI_WORKFLOW}" --event "${CI_EVENT}" --wait --timeout 1800 --interval 15 --format json

git fetch origin --prune
test "$(git rev-parse --verify "${REMOTE_FEATURE_REF}^{commit}")" = "${EXPECTED_FEATURE_HEAD}"
git merge-base --is-ancestor "${REMOTE_FEATURE_REF}" "${REMOTE_MAIN_REF}"
git push origin --delete "${FEATURE_BRANCH}"
git fetch origin --prune
if git show-ref --verify --quiet "${REMOTE_FEATURE_REF}"; then
  echo "ERROR: remote feature ref still exists" >&2
  echo MERGE_CLEANUP_BLOCKED
  exit 1
fi
test "$(git rev-parse --verify "${REMOTE_MAIN_REF}^{commit}")" = "${MERGE_SHA}"
test "$(git rev-parse --verify "${LOCAL_FEATURE_REF}^{commit}")" = "${EXPECTED_FEATURE_HEAD}"
test "$(git rev-parse --verify "${LOCAL_MAIN_REF}^{commit}")" = "${MERGE_SHA}"
test "$(cat VERSION)" = "${EXPECTED_VERSION}"
test -z "$(git status --porcelain)"
```

The exact merge-SHA CI phase is mandatory before cleanup. The cleanup command must delete only the remote feature branch; do not rerun or dispatch workflows, and do not delete the local feature branch.
Use the compact report contract. Return `MERGE_FINALIZED`,
`MERGE_CLEANUP_BLOCKED`, or pre-merge `MERGE_BLOCKED`.
