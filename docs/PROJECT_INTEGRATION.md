# Project Integration

This repository uses Option A:

- central canonical workflow repository;
- managed block in project `AGENTS.md`;
- exact pin in project `.gpt-workflow.lock`;
- no copied workflow document in each project.

Integrated projects also carry one explicit `release-publication.json`
declaration. `none` projects must not contain `release-config.json` or any of
the four canonical release/publication scripts. `tag_only` and
`github_actions` projects must contain `release-config.json`,
`scripts/release.py`, `scripts/check-github-ci.py`,
`scripts/validate-release-publication.py`, and
`scripts/verify-release-publication.py`; all four scripts must pass planner
conformance. See [`RELEASE_PUBLICATION.md`](RELEASE_PUBLICATION.md).

## Install

```bash
bash setup.sh \
  --project /path/to/project \
  --version <VERSION> \
  --release-publication-file /path/to/release-publication.json
```

## Update

```bash
bash update.sh --project /path/to/project --version <VERSION>
```

The setup declaration input is mandatory and is validated before the managed
block or lock is written. Update reuses the project's already-installed
declaration and fails closed when it is missing or invalid. Agents must not
infer a mode or silently create a `none` declaration.

Both scripts are idempotent. The managed block is replaced rather than duplicated.

## Offline limitation

Option A requires the agent to obtain the pinned workflow from the canonical
repository at least once. For fully offline work, include a workflow snapshot
inside the task's patch pack without changing the project integration model.
