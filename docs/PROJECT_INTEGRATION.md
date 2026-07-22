# Project Integration

This repository uses Option A:

- central canonical workflow repository;
- managed block in project `AGENTS.md`;
- exact pin in project `.gpt-workflow.lock`;
- no copied workflow document in each project.

## Install

```bash
bash setup.sh --project /path/to/project --version v1.0.0
```

## Update

```bash
bash update.sh --project /path/to/project --version v1.1.0
```

Both scripts are idempotent. The managed block is replaced rather than duplicated.

## Offline limitation

Option A requires the agent to obtain the pinned workflow from the canonical
repository at least once. For fully offline work, include a workflow snapshot
inside the task's patch pack without changing the project integration model.
