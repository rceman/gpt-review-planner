# Release Process

## Authority model

`VERSION` is the canonical version source. `release-config.json` declares every file that must carry the same version. `scripts/release.py` is the only supported mutation mechanism.

The script is repository-local and dependency-free. It supports plain-text version files, JSON fields, and selected TOML table keys. Package ecosystems are included only when listed in `release-config.json`; no file is guessed or modified implicitly.

## Commands

### Check consistency

```bash
python scripts/release.py check
```

This verifies semantic-version syntax, equality across configured files, and forbidden concrete project-version literals in documentation such as `README.md`.

### Prepare a version

```bash
python scripts/release.py prepare X.Y.Z
```

The repository must be clean. The command updates all present configured version files, promotes the populated `Unreleased` changelog section to the selected version and UTC date when configured, and leaves the changes uncommitted for review and agent-executed quality gates.

### Commit the version

```bash
python scripts/release.py commit
```

Only configured version-file changes may be present. The script stages them and creates the configured release commit. It does not push.

### Create the tag

```bash
python scripts/release.py tag
```

The repository must be clean. The script creates an annotated `vX.Y.Z` tag and refuses to overwrite an existing tag. It does not push.

### Verify a tag

```bash
python scripts/release.py verify-tag "${GITHUB_REF_NAME:-vX.Y.Z}"
```

The tag must match `VERSION` and resolve to the checked-out commit. Tag-triggered GitHub Actions must run this command before publishing a Release.

## Required order

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

The version is not incremented automatically on every merge. The project owner or approved release task selects the next semantic version; the script applies that decision consistently.

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
  scripts/*.sh \
  templates/executable-patch-pack/scripts/*.sh

python3 -m compileall -q scripts tests examples

python3 -m unittest discover -s tests -v

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
