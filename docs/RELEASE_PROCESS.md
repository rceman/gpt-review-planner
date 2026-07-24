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
