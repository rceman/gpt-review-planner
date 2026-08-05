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

Every integrated project also carries regular, non-symlink
`project-workflow.json` and `quality-gates.json` declarations. Setup validates
both with the pinned planner validators before mutation; agents read and
validate them before task authoring and must not execute declaration commands
outside future deterministic tooling.

## Install

```bash
bash setup.sh \
  --project /path/to/project \
  --version <VERSION> \
  --release-publication-file /path/to/release-publication.json \
  --project-workflow-file /path/to/project-workflow.json \
  --quality-gates-file /path/to/quality-gates.json
```

## Update

```bash
bash update.sh --project /path/to/project --version <VERSION>
```

All three setup declaration inputs are mandatory and are validated before the
managed block, lock, or declaration files are written. Update forwards
explicit inputs when supplied; otherwise it uses only the project's existing
root `release-publication.json`, `project-workflow.json`, and `quality-gates.json`
files and fails closed when any is missing or invalid. Agents must not infer a
mode or silently create a declaration.

Both scripts are idempotent. The managed block is replaced rather than duplicated.

## Offline limitation

Option A requires the agent to obtain the pinned workflow from the canonical
repository at least once. For fully offline work, include a workflow snapshot
inside the task's patch pack without changing the project integration model.
