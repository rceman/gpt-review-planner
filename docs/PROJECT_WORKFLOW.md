# Project workflow declaration

`project-workflow.json` is the strict, dependency-free declaration of project
branching ownership and CI policy. The canonical initial declaration is the
template at [`templates/project/project-workflow.json`](../templates/project/project-workflow.json);
the planner and gateway fixtures must remain byte-identical to it until a
project-specific contract is explicitly approved.

Validate a declaration with:

```bash
python3 scripts/validate-project-workflow.py project-workflow.json
```

## Admission and agent boundary

`main` is the default branch and `develop` is the integration branch. Merge
into `develop` is the next-release admission point. Deferred tasks remain
outside `develop` until their owner-approved admission work is complete.

The agent has one active task and stops after one clean, pushed task commit.
The agent does not wait for CI, own merge, own release, or rewrite reviewed
history. Task CI is disabled by the canonical initial declaration; merge and
release CI are observed rather than made agent blockers.

The target version is selected only at release publication. This declaration
does not prepare commits, create branches, merge, release, publish telemetry,
or adopt a root `project-workflow.json`; those are separate bounded slices.

Stale task work receives a new revision branch using the `-r{revision}` suffix.
The quality contract is the canonical repository-relative
`quality-gates.json`, and preparation before a task commit is required.
