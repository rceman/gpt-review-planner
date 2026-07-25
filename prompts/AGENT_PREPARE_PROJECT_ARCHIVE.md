# Prepare Universal Project Archive

Prepare a review archive with filesystem and Git access.

Required inputs:

- source project path;
- owner-selected immutable GPT Review Planner tag or exact commit;
- output archive path;
- optional relative `AGENTS.md` path;
- optional `<OWNER_TASK_OBJECTIVE>`;
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

`staging` is the default. Expected downstream workflow is metadata only and
must not alter archive contents or lock behavior. An empty objective means a
complete static review. Both downstream workflows receive the same complete
archive, including source, tests, fixtures, specifications, ADRs, docs,
dependency manifests and lockfiles, migrations, CI/configuration, operational
scripts, required assets, generated source that is intentionally versioned,
`.gpt-workflow.lock`, managed `AGENTS.md`, and
`.gpt-review/archive-manifest.json`.

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
6. Set `PLANNER_DIR` to a checkout of the exact owner-selected workflow
   revision. Run only `$PLANNER_DIR/setup.sh` against staging, passing the
   explicit `--version` or exact `--commit`. Generate the lock and managed
   `AGENTS.md` through official tooling only.
7. Run `python3 "$PLANNER_DIR/scripts/validate-project-integration.py"`
   against staging, passing `--agents-file` when a custom relative AGENTS path
   was selected.
8. Generate `.gpt-review/archive-manifest.json` from the source state, generated
   lock, selected downstream metadata, and UTC timestamp. Never hand-author the
   workflow lock or guess its identity.
9. Run the dependency-free manifest validator:

   ```bash
   python3 "$PLANNER_DIR/scripts/validate-project-archive-manifest.py" \
     <STAGED_PROJECT_ROOT>/.gpt-review/archive-manifest.json \
     --project-root <STAGED_PROJECT_ROOT> --staging
   ```

   A lock/manifest mismatch, malformed metadata, invalid workflow enum, or
   staging source-modified value is fatal.
10. Archive staging, generate an external SHA-256 sidecar, inspect contents, and
   delete temporary staging data after successful creation.

## Integrate-source mode

Use only when explicitly requested. Run official `setup.sh` or `update.sh`
directly against the source, review exact lock and managed `AGENTS.md` changes,
validate integration, and do not commit unless separately requested. Do not mix
workflow integration with unrelated project changes.

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
confirmation, selected downstream workflow, and deviations. The archive SHA is
never written into the manifest.

The archive must contain source, a valid generated lock, and the managed planner
block. It must not contain secrets or build pollution. The source remains
unchanged in staging mode.
