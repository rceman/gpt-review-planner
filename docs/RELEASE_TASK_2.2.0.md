# Task-specific release lifecycle declaration

This file is the source/handoff record for the owner-authorized planner source
update and is not a reusable release policy.

Release lifecycle mode: implementation_unreleased

Release target version: 2.2.0

The task advances synchronized source version fields to `2.2.0`, adds accepted
notes only under `## Unreleased`, and requires these exact implementation gates:

```text
python3 scripts/validate-release-tool-conformance.py --release-script scripts/release.py --ci-script scripts/check-github-ci.py
python3 scripts/release.py check-source
python3 scripts/release.py check
```

It forbids dated release headings, release commits, tags, publication,
installation, deployment, restart, and connector actions. This file is the
task-specific immutable handoff record; reusable lifecycle policy remains
version-agnostic.
