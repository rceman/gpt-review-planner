# Post-Merge Branch Cleanup Contract

This is the normative procedure for finalizing a completed feature merge.
`MERGE_READY` and `MERGE_FINALIZED` are different states.

## Terminal statuses

`MERGE_READY` is the terminal review verdict. It means review closure passed,
the feature is authorized for merge, and no merge blocker remains. It does not
claim that Git integration has happened.

`MERGE_FINALIZED` may be reported only after the expected feature head was
merged with the expected parents, the canonical remote-tracking main ref points
to the exact merge commit, exact-SHA CI succeeded, and the safe remote cleanup
below completed.

`MERGE_CLEANUP_BLOCKED` is used only when merge and merge CI succeeded but safe
remote branch deletion could not be completed. The merge remains valid, but
finalization is incomplete. Report the exact failed command and observed state;
do not retry through alternate transports or APIs.

## Required post-merge sequence

Use the reviewed feature branch and immutable expected values supplied by the
owner. Remote deletion is permitted only after exact merge-SHA CI succeeds.

```bash
FEATURE_BRANCH="<FEATURE_BRANCH>"
REMOTE_MAIN_REF="refs/remotes/origin/main"
REMOTE_FEATURE_REF="refs/remotes/origin/${FEATURE_BRANCH}"
LOCAL_FEATURE_REF="refs/heads/${FEATURE_BRANCH}"

git fetch origin --prune

test "$(git rev-parse --verify "${REMOTE_MAIN_REF}^{commit}")" = \
  "<EXPECTED_MERGE_SHA>"

test "$(git rev-parse --verify "${REMOTE_FEATURE_REF}^{commit}")" = \
  "<EXPECTED_FEATURE_HEAD>"

git merge-base --is-ancestor \
  "${REMOTE_FEATURE_REF}" \
  "${REMOTE_MAIN_REF}"

git push origin --delete "${FEATURE_BRANCH}"

git fetch origin --prune

if git show-ref --verify --quiet "${REMOTE_FEATURE_REF}"; then
  echo "ERROR: deleted remote feature ref still exists" >&2
  exit 1
fi

test "$(git rev-parse --verify "${REMOTE_MAIN_REF}^{commit}")" = \
  "<EXPECTED_MERGE_SHA>"

test "$(git rev-parse --verify "${LOCAL_FEATURE_REF}^{commit}")" = \
  "<EXPECTED_FEATURE_HEAD>"
```

The deletion command uses the feature branch name without the `origin/`
prefix. Then verify:

- `refs/remotes/origin/${FEATURE_BRANCH}` does not exist;
- `refs/remotes/origin/main` still equals `<EXPECTED_MERGE_SHA>`;
- the local `<FEATURE_BRANCH>` still exists and still points to its previous tip;
- no tracked or untracked repository files were created by cleanup;
- the worktree is clean.

The final merge report must include the feature branch, reviewed feature head,
merge SHA and parents, merge CI run/job/exact SHA/URL/conclusion, ancestry
result, deletion command and result, final remote inventory, retained local
branch and tip, final `refs/remotes/origin/main`, VERSION, worktree state, and exactly one
of `MERGE_FINALIZED` or `MERGE_CLEANUP_BLOCKED`.

## Safety and transport rules

Never delete `origin/main` or `origin/HEAD`. Never delete a branch whose tip is
not an ancestor of `refs/remotes/origin/main`, or whose current remote tip differs from the
reviewed and merged feature head. Merged state cannot be inferred from a branch
name, age, commit message, or an empty three-dot diff.

Abbreviated names such as `origin/main` and `origin/<FEATURE_BRANCH>` MUST NOT
be used for authoritative identity, ancestry, existence, or retention checks.
A local branch named `origin/main` may shadow or make an abbreviated name
ambiguous. `refs/remotes/origin/main` is the canonical remote-tracking main
ref, `refs/remotes/origin/<FEATURE_BRANCH>` is the canonical remote feature
ref, and `refs/heads/<FEATURE_BRANCH>` is the canonical retained local feature
ref. Existing unrelated local branches, including `refs/heads/origin/main`,
are not modified during cleanup.

Never rename merged branches to `merged/*` or `archive/*`, delete the local
feature branch, or use `git branch -d` or `git branch -D` during finalization.
Use only the existing configured `origin`, which must use the repository's
established SSH transport. If it does not, stop and report the actual origin
URL; do not rewrite it. Never use a fallback HTTPS remote, `gh`, GitHub REST or
GraphQL APIs, repository-setting mutation, force-push, squash, rebase,
cherry-pick, amend, reset, or history rewriting.

The current evidence ancestry model remains unchanged: implementation and
evidence commits remain individually reachable, feature integration uses
`git merge --no-ff`, and squash merges are forbidden. Deleting a merged remote
branch does not delete its commits because they remain reachable from `main`.
The retained local branch is a convenience and is not repository evidence.

If any safety check fails, stop and report the exact state. Do not delete the
branch and use `MERGE_CLEANUP_BLOCKED` only after merge and exact-SHA CI have
succeeded.
