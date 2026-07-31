# Versioning

The workflow uses semantic versioning and immutable Git tags.

- PATCH: clarification or backward-compatible correction.
- MINOR: backward-compatible process or tooling addition.
- MAJOR: incompatible responsibility, artifact-contract, or execution-order change.

The active workflow filename remains:

```text
GPT_REVIEW_PLANNER.md
```

## Canonical version source

`VERSION` is canonical. `release-config.json` lists every other version-bearing file. Version files must be synchronized only through:

```bash
python scripts/release.py prepare X.Y.Z
```

`README.md` must not contain a concrete current project version. Published versions are discovered through immutable `vX.Y.Z` tags and GitHub Releases.

Projects pin both the selected tag and its exact commit in `.gpt-workflow.lock`.

Workflow 2.0.0 is an incompatible cutover to the explicit, v2-only execution
and evidence contracts. New tasks must use GPT Patch Pack v2 and declare one
execution mode; historical v1 artifacts remain immutable history and are not
read, migrated, or negotiated by current tooling. The cutover does not change
the version during this correction task; a later release decision is separate.

See [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md).
