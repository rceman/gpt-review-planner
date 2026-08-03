# Release Process

Final release reports follow [`AGENT_REPORTING.md`](AGENT_REPORTING.md): use one `Release CI` record and one `Tag CI` record without repeating their fields.

Before release mutation, read [`HOST_PREREQUISITES.md`](HOST_PREREQUISITES.md), [`RUNTIME_UPGRADE_POLICY.md`](RUNTIME_UPGRADE_POLICY.md), and [`PERSISTED_STATE_MIGRATION_POLICY.md`](PERSISTED_STATE_MIGRATION_POLICY.md). A release that changes persisted state must declare migration authorization, target-decoder validation, backup, atomic commit, rollback, installed/running version proof, and rehearsal from the previous production-like state. Run `python3 scripts/validate-runtime-upgrade-task.py <TASK_JSON>` before any runtime activation.

## Authority model

`VERSION` is the canonical version source. `release-config.json` declares every file that must carry the same version. `scripts/release.py` is the only supported mutation mechanism.

The two-mode policy in [`RELEASE_LIFECYCLE.md`](RELEASE_LIFECYCLE.md) is
normative. Every version-touching task declares exactly one of
`implementation_unreleased` or `release_publication` and an owner-selected
target version in its immutable task and task-specific handoff record.

The script is repository-local and dependency-free. It supports plain-text version files, JSON fields, and selected TOML table keys. Package ecosystems are included only when listed in `release-config.json`; no file is guessed or modified implicitly.

Before `MERGE_READY`, a release-surface task must pass the immutable task
projection validator and prove the attached project's two-script conformance:

```bash
python3 scripts/validate-release-lifecycle-task.py <IMMUTABLE_TASK_JSON>
python3 scripts/validate-release-tool-conformance.py \
  --release-script scripts/release.py \
  --ci-script scripts/check-github-ci.py
```

Required CI gates use the exact checked-out commit rather than a manually
copied SHA:

```bash
python3 scripts/check-github-ci.py \
  --repository OWNER/REPO \
  --sha-from-git HEAD \
  --policy required \
  --wait \
  --format json
```

The lifecycle task validator accepts only the canonical command names
`check-source`, `check-release-ready`, and `check-tag-ready`, and enforces the
mode-specific order declared in the immutable task.

## Commands

### Check consistency

```bash
python scripts/release.py check
```

This verifies semantic-version syntax, equality across configured files, and forbidden concrete project-version literals in documentation such as `README.md`.

### Check implementation source state

```bash
python3 scripts/release.py check-source
```

This is the required gate for `implementation_unreleased`: the worktree is
clean, configured versions agree, `Unreleased` is non-empty, the current
version has no dated heading, and its target tag does not exist.

### Prepare a version

```bash
python scripts/release.py prepare X.Y.Z
```

The repository must be clean. The command fully validates before mutation,
then promotes the populated `Unreleased` changelog section to the selected
version and UTC date. It supports current `<target` by synchronizing configured
version files and current `== target` by leaving those files byte-identical and
creating only the necessary release metadata changes.

### Check release-ready state

```bash
python3 scripts/release.py check-release-ready
```

Run this only after `prepare`. It validates the prepared release diff before
the release commit: synchronized target versions, exactly one dated target
heading, an empty `Unreleased` section, and only the actual configured
release-file subset changed. It does not precede preparation or release
mutation.

### Commit the version

```bash
python scripts/release.py commit
```

The command requires `check-release-ready` state, stages only the actual
non-empty subset of configured version files plus the changelog, permits a
changelog-only commit for a pre-set target, rejects unrelated or empty commits,
and creates the configured release message. It does not push.

### Create the tag

```bash
python scripts/release.py tag
```

The repository must be clean and pass `check-tag-ready`. The script creates an
annotated `vX.Y.Z` tag and refuses to overwrite an existing tag. It does not
push.

### Check tag-ready state

```bash
python3 scripts/release.py check-tag-ready
```

This requires release-ready state, a clean worktree, the configured release
commit identity, and an absent target tag.

### Verify a tag

```bash
python scripts/release.py verify-tag "${GITHUB_REF_NAME:-vX.Y.Z}"
```

The tag must be annotated, match `VERSION`, and resolve to the checked-out
commit. Tag-triggered GitHub Actions must run this command before publishing a
Release.

## Required order

Before release mutation and before evidence creation, complete the [host prerequisite](HOST_PREREQUISITES.md) preflight:

```bash
python3 --version
python3 -m pytest --version
```

A missing required runner must be installed or resolved before `scripts/release.py prepare`, the release commit, committed evidence, or tag creation.

```text
implementation and tests written
→ version prepared
→ agent quality gates
→ release commit
→ push or merge
→ CI passes on release commit
→ tag created and pushed
→ release artifacts verified
```

The canonical publication order is:

```text
prepare → check-release-ready → commit → exact release-commit CI
→ check-tag-ready → tag → verify-tag
```

The version is not incremented automatically on every merge. The project owner
or approved lifecycle task selects the next semantic version; the script
applies that decision consistently. A missing lifecycle declaration, wrong
state gate, or failed conformance proof prevents `MERGE_READY`.

## Configuration examples

Plain canonical file:

```json
{"path": "VERSION", "kind": "plain"}
```

JSON package manifest:

```json
{"path": "package.json", "kind": "json", "pointer": "/version", "optional": true}
```

Composer manifest when a project intentionally stores a version field:

```json
{"path": "composer.json", "kind": "json", "pointer": "/version", "optional": true}
```

Cargo workspace manifest:

```json
{"path": "Cargo.toml", "kind": "toml", "table": "workspace.package", "key": "version", "optional": true}
```

Optional files are skipped when absent. Existing required files with missing or malformed version locations are fatal errors.

## Operational release procedure

The following procedure is authoritative for every future release. The owner
must explicitly provide `<TARGET_VERSION>`; the agent must never infer or
autonomously select it.

### Preconditions

Synchronize `main` and verify the release contract before mutation:

```bash
git fetch --all --prune
git switch main
git pull --ff-only origin main
git status --short --branch
git rev-parse HEAD
cat VERSION
python3 scripts/release.py check
git tag --list '<TAG>'
git ls-remote --tags origin 'refs/tags/<TAG>'
```

Local `main` must equal `origin/main`, the worktree must be clean apart from
ignored local files such as `.idea/`, and `<TAG>` must not exist locally or
remotely. Preserve ignored local files untouched. An optional local safety
branch may be created before mutation:

```bash
backup_branch="backup/main-before-release-$(date -u +%Y%m%d-%H%M%S)"
git branch "$backup_branch" HEAD
```

If `main` has moved unexpectedly or any precondition fails, stop and report the
exact state.

### Prepare phase

Use the automation exactly as follows:

```bash
python3 scripts/release.py check
python3 scripts/release.py prepare <TARGET_VERSION>
git status --short
git diff -- VERSION CHANGELOG.md
git diff --check
python3 scripts/release.py check
```

Review the exact changed paths, `VERSION`, and `CHANGELOG.md`. Confirm that a
non-empty `Unreleased` section was promoted to the target release section and
UTC date, and that no unrelated path changed. If the section is empty,
malformed, or inaccurate, stop; do not invent release notes.

### Required pre-release gates

Run all required gates before creating the release commit:

```bash
bash -n \
  setup.sh \
  update.sh \
  scripts/*.sh

python3 -m compileall -q scripts tests examples

python3 -m unittest discover -s tests -v
python3 scripts/selftest-gpt-patch-pack-v2.py

The self-test is a release blocker for runner, builder, schema, template, delivery, or format changes.

python3 -m unittest discover \
  -s examples/rust-domain-feature/reference/python \
  -v

python3 -m pytest -q

python3 scripts/release.py check

git diff --check
```

The unittest command is the declared repository unit gate. Pytest is
supplemental unless separately declared in repository configuration. A failed
required gate prevents commit and tagging. Do not mix unrelated production
fixes into a release commit.

### Release commit

Create the release commit only through the script:

```bash
python3 scripts/release.py commit
```

Verify the configured message `chore(release): v<TARGET_VERSION>`, exact
configured version/changelog paths, `VERSION=<TARGET_VERSION>`, and a clean
worktree:

```bash
git show --stat --oneline HEAD
git show --name-status --format= HEAD
git status --short
cat VERSION
```

### Push and release-commit CI

Push normally:

```bash
git push origin main
```

Never force-push. Wait for CI associated with the exact `<RELEASE_COMMIT>` SHA
and record `<CI_RUN_ID>`, `<CI_JOB_ID>`, `<CI_URL>`, and the conclusion
externally. Do not create a tag until release-commit CI succeeds. Refetch and
verify that `origin/main` still equals `<RELEASE_COMMIT>` before tagging; stop
if `main` moved.

### Annotated tag

Create and verify the annotated tag through the automation:

```bash
python3 scripts/release.py tag
python3 scripts/release.py verify-tag <TAG>
git show --no-patch --decorate <TAG>
git rev-parse '<TAG>^{commit}'
git rev-parse HEAD
```

The tag must match `VERSION`, resolve exactly to `<RELEASE_COMMIT>`, be
annotated, and leave a clean worktree. Existing tags must never be overwritten.

### Explicit tag push

Push only the selected tag:

```bash
git push origin <TAG>
```

Do not use `git push --tags`. Wait for all tag-triggered workflows to complete
successfully and verify tag/version identity.

### Final verification

```bash
git fetch --tags origin
test "$(git rev-parse origin/main)" = "<RELEASE_COMMIT>"
test "$(git rev-parse '<TAG>^{commit}')" = "<RELEASE_COMMIT>"
python3 scripts/release.py check
python3 scripts/release.py verify-tag <TAG>
git status --short --branch
git log --decorate --oneline -5
```

The worktree must remain clean. A GitHub Release is not part of this procedure
unless the owner explicitly authorizes it; do not create one automatically.
A GitHub Release requires explicit owner authorization.

### Failure handling

For a dirty worktree, malformed or empty changelog section, existing target tag,
quality-gate failure, release-commit CI failure, `main` moving before tagging,
branch-protection rejection, tag-push rejection, or tag-triggered CI failure:

- do not force, bypass validation, or change protection settings;
- do not rewrite published history or amend a published release commit/tag;
- do not create or push a replacement tag;
- stop and report the exact command, state, paths, and CI evidence.

### Final agent report

Report:

1. previous main SHA;
2. target version;
3. release commit SHA;
4. exact changed files;
5. local gate results and test counts;
6. release-commit CI run, job, URL, and conclusion;
7. annotated tag and tag verification;
8. tag-triggered CI run, job, URL, and conclusion;
9. remote main/tag identity;
10. confirmation that no force-push, rebase, squash, manual version editing,
    broad tag push, or unauthorized GitHub Release occurred.
CI policy is capability-aware: an observed exact-SHA failure blocks, while permitted CI absence does not. Local runtime gates remain mandatory.
