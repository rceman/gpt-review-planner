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

See [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md).
