# Agent Merge Finalization

Load `docs/PROCEDURE_INDEX.md`, `docs/AGENT_REPORTING.md`, and `docs/POST_MERGE_BRANCH_CLEANUP.md` from the exact pinned planner checkout before acting.

Parameters: `<REPOSITORY>`, `<LOCAL_REPOSITORY>`, `<SSH_ORIGIN>`, `<MAIN_BRANCH>`, `<FEATURE_BRANCH>`, `<EXPECTED_MAIN_BEFORE>`, `<EXPECTED_FEATURE_HEAD>`, `<EXPECTED_VERSION>`, `<CI_POLICY>`, `<CI_WORKFLOW>`, `<CI_EVENT>`.

Verify exact repository, SSH origin, clean worktree, VERSION, and fully qualified refs: `refs/remotes/origin/main`, `refs/remotes/origin/<FEATURE_BRANCH>`, `refs/heads/main`, and `refs/heads/<FEATURE_BRANCH>`. Verify immutable tips, ancestry, and no unexpected divergence. Switch to main and run normal `git merge --no-ff`.

Verify the merge has exactly two ordered parents: `<EXPECTED_MAIN_BEFORE>` and `<EXPECTED_FEATURE_HEAD>`, verify feature ancestry and unchanged tree/content, then push main normally. Query exact merge-SHA CI with the pinned helper and `<CI_POLICY>`, `<CI_WORKFLOW>`, and `<CI_EVENT>`. Do not rerun or dispatch workflows.

Only after successful exact merge-SHA CI, reverify remote feature identity and ancestry, delete only the remote `<FEATURE_BRANCH>`, fetch/prune, verify remote feature-ref absence, retain the local feature branch, verify main identity, VERSION, and a clean worktree.

Return exactly one terminal status: `MERGE_FINALIZED`, `MERGE_CLEANUP_BLOCKED`, or pre-merge `MERGE_BLOCKED`. Use the compact CI projection from `docs/AGENT_REPORTING.md`; do not paste successful helper JSON and repeat its fields.
