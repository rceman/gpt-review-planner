# Prepare Project Archive for Review

Prepare a review archive with filesystem and Git access.

Required inputs:

- source project path;
- owner-selected immutable GPT Review Planner tag or exact commit;
- output archive path;
- optional relative `AGENTS.md` path;
- optional `<OWNER_TASK_OBJECTIVE>`;
- mode: `staging` (default) or `integrate-source`.

Never infer `latest`, and never hand-write `.gpt-workflow.lock`.

## Staging mode

1. Inspect source root, readable files, Git status, branch, and revision. Stop
   on unresolved conflicts, a missing root, or unreadable required content.
2. Stop by default on a dirty worktree. Include dirty changes only after an
   explicit owner request and report the dirty state accurately.
3. If an existing lock is present, validate it. Preserve a matching lock; stop
   on a mismatch unless an explicit workflow update is authorized. Use
   `update.sh` only for that authorized update.
4. Create a temporary staging directory and copy reviewable project content
   without altering the source repository.
5. Exclude `.git`, dependency directories, build outputs, caches, test/runtime
   artifacts, IDE/OS metadata, credentials, private keys, `.env` secrets, and
   unrelated large binaries. Preserve intentionally versioned fixtures and
   required binary assets.
6. Run the pinned official `setup.sh` against staging, passing the owner-selected
   explicit `--version` or exact `--commit`. Generate the lock and managed
   `AGENTS.md` through official tooling only.
7. Run `scripts/validate-project-integration.py` against staging.
8. Add a generic task-intent file only if the repository workflow already defines
   one; do not invent an undocumented contract.
9. Archive staging, generate an external SHA-256 sidecar, inspect contents, and
   delete temporary staging data after successful creation.

## Integrate-source mode

Use only when explicitly requested. Run official `setup.sh` or `update.sh`
directly against the source, review exact lock and managed `AGENTS.md` changes,
validate integration, and do not commit unless separately requested. Do not mix
workflow integration with unrelated project changes.

## Report

Return source project, branch/revision, clean/dirty status, selected workflow
repository/version/commit, mode, generated lock path, generated/updated
`AGENTS.md` path, validation result, excluded categories, archive path/root,
file count, size, SHA-256, source-modification confirmation, and deviations.

The archive must contain source, a valid generated lock, and the managed planner
block. It must not contain secrets or build pollution. The source remains
unchanged in staging mode.
