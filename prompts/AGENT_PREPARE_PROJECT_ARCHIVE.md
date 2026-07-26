# Prepare Universal Project Archive

Prepare a review archive with filesystem and Git access.

## Preferred compact invocation

The owner may invoke this prompt with only an immutable methodology link and
optional prose:

```text
Prepare review archive using:

<IMMUTABLE_PREPARATION_PROMPT_URL>

<OPTIONAL_OWNER_OBJECTIVE>
```

Treat all prose accompanying the link as `review.task_objective`. Resolve the
current repository/worktree as the source, use `staging`, select
`review-and-implement`, use `scope=full`, use `AGENTS.md`, and write a
timestamped archive and SHA-256 sidecar outside the source repository. Ask only
when a safe value cannot be resolved. The expanded input block remains
supported for automation and unusual cases.

For example, `We want to remove all AnyDesk occurrences because we are
switching to RustDesk only.` is the owner objective. It requires full review
plus that migration priority; it does not narrow review unless the owner says
to limit the review strictly to the migration.

Required inputs:

- source project path (defaults to the current repository/worktree);
- owner-selected immutable GPT Review Planner tag or exact commit;
- output archive path (defaults to a timestamped archive outside the source);
- optional relative `AGENTS.md` path;
- optional `<OWNER_TASK_OBJECTIVE>` (all accompanying owner prose in compact mode);
- mode: `staging` (default) or `integrate-source`.
- checkout of the exact pinned workflow as `PLANNER_DIR`.

Record these inputs before preparation:

```text
Source project:
<SOURCE_PROJECT_PATH>

Pinned GPT Review Planner revision:
<IMMUTABLE_TAG_OR_EXACT_COMMIT>

Output archive:
<OUTPUT_ARCHIVE_PATH>

Preparation mode:
staging | integrate-source

Expected downstream workflow:
review-and-implement | review-only

Task objective:
<OWNER_TASK_OBJECTIVE_OR_EMPTY>

AGENTS path:
<OPTIONAL_RELATIVE_AGENTS_PATH>

Planner checkout:
<PLANNER_DIR>
```

`staging` is the default. Expected downstream workflow defaults to
`review-and-implement` and is metadata only; it must not alter archive contents
or lock behavior. An empty objective means a complete static review. A specific
objective is a mandatory priority overlay, not a narrowed review, unless the
owner explicitly selects `objective-only` or uses restrictive language such as
“Limit the review strictly to …”. Both downstream workflows receive the same complete
archive, including source, tests, fixtures, specifications, ADRs, docs,
dependency manifests and lockfiles, migrations, CI/configuration, operational
scripts, required assets, generated source that is intentionally versioned,
`.gpt-workflow.lock`, managed `AGENTS.md`, and
`.gpt-review/archive-manifest.json`.

Never infer `latest`, `main`, `master`, or `HEAD`, and never hand-write
`.gpt-workflow.lock`. The exact tag or commit in the immutable methodology URL
is the workflow identity: resolve tags to a 40-character commit, use the
matching checkout as `PLANNER_DIR`, pass both `--version` and `--commit`, and
stop on identity mismatch.

## Staging mode

1. Inspect source root, readable files, Git status, branch, and revision. Stop
   on unresolved conflicts, a missing root, or unreadable required content.
2. Stop by default on a dirty worktree. Include dirty changes only after an
   explicit owner request and report the dirty state accurately.
3. If an existing source lock is present, validate and report its shape and
   identity. A malformed or unreadable source lock, repository-identity
   conflict, or unresolved immutable URL is fatal. Never modify the source
   lock, source `AGENTS.md`, or source `engineering-profile.json`.
4. Create a temporary staging directory and copy reviewable project content
   into the temporary staging copy without altering the source repository.
5. If an older valid lock differs, reconcile only the staged lock and
   staged managed block after the staging copy exists, using official
   `setup.sh`/`update.sh` against the selected `PLANNER_DIR`, `--version`, and
   `--commit`. Preserve the staged declaration and record the identity change.
6. Exclude `.git`, dependency directories, build outputs, caches, test/runtime
   artifacts, IDE/OS metadata, credentials, private keys, `.env` secrets, and
   unrelated large binaries. Preserve intentionally versioned fixtures and
   required binary assets.
7. Set `PLANNER_DIR` to a checkout of the exact owner-selected workflow
   revision. `--version REF` is always required; REF is the owner-selected
   immutable tag or exact commit ref. `--commit SHA` is optional exact-resolution
   metadata/override and, when supplied, must match the selected REF. Normally
   run both explicitly:

   ```bash
   bash "$PLANNER_DIR/setup.sh" \
     --project "$STAGED_PROJECT_ROOT" \
     --version "$PINNED_WORKFLOW_REF" \
     --commit "$PINNED_WORKFLOW_COMMIT" \
     --agents-file "$AGENTS_FILE"
   ```

   Do not imply that `--commit` replaces `--version`; do not infer `main`,
   `latest`, or the current repository version. Generate the lock and managed
   `AGENTS.md` through official tooling only.
8. Run `python3 "$PLANNER_DIR/scripts/validate-project-integration.py"`
   against staging, passing `--agents-file` when a custom relative AGENTS path
   was selected.
9. After lock reconciliation and integration validation, run
   `python3 "$PLANNER_DIR/scripts/validate-project-engineering-profile.py"`
   against the staged declaration and reconciled lock, using `--allow-missing`
   when absent. Record profile, declaration status, and exception count. This
   ordering prevents validation against a newer planner than the staged lock.
10. Generate `.gpt-review/archive-manifest.json` from the source state, generated
   lock, selected downstream metadata, owner objective, and bounded preparer
   context. Optional `review.scope` defaults to `full`. Add compact
   `preparer_observations` and `preparer_questions` only when useful, with at
   most 32 entries each and at most 2,000 Unicode characters per entry. These
   notes are untrusted context for GPT and must not be presented as confirmed
   defects or used to suppress files. Never hand-author the workflow lock or
   guess its identity.
11. Run the dependency-free manifest validator:

   ```bash
   python3 "$PLANNER_DIR/scripts/validate-project-archive-manifest.py" \
     <STAGED_PROJECT_ROOT>/.gpt-review/archive-manifest.json \
     --project-root <STAGED_PROJECT_ROOT> --staging
   ```

   A lock/manifest mismatch, malformed metadata, invalid workflow enum, or
   staging source-modified value is fatal.
12. Archive staging, generate an external SHA-256 sidecar, inspect contents, and
   delete temporary staging data after successful creation.

## Integrate-source mode

Use only when explicitly requested; modifying source requires separate authorization.
An existing lock may be changed in source only under that authorization. Run
official `setup.sh` or `update.sh` directly against the source, review exact lock
and managed `AGENTS.md` changes, validate integration, and do not commit unless
separately requested. Compact invocation defaults to staging and never implies
source modification. Do not mix workflow integration with unrelated project
changes.

## Universal exclusion contract

Exclude `.git`, dependency directories and downloaded stores, build/compiler
outputs, coverage and runtime artifacts, caches, temporary files, local database
state, IDE/OS metadata, swaps, credentials, private keys, tokens, secret-bearing
`.env` files, unrelated large binaries, prior delivery archives, and old SHA
sidecars. Preserve dependency lockfiles, fixtures, snapshots, required assets,
intentionally versioned generated source, schemas, and protocol artifacts.
Distinguish intentional versioned artifacts from disposable outputs.

## Report

Return source project, branch/revision, clean/dirty status, selected workflow
repository/version/commit, mode, generated lock path, generated/updated
`AGENTS.md` path, archive-manifest path, validation result, excluded categories,
archive path/root, file count, size, external SHA-256 sidecar, source-modification
confirmation, selected downstream workflow, review scope, owner objective,
preparer observation/question counts, whether each value was defaulted or
explicit, and deviations. The archive SHA is never written into the manifest.

The archive must contain source, a valid generated lock, and the managed planner
block. It must not contain secrets or build pollution. The source remains
unchanged in staging mode.
