# Task-specific release lifecycle declaration

This file is the source/handoff record for the owner-authorized planner source
update and is not a reusable release policy.

Release lifecycle mode: implementation_unreleased

Release target version: 2.2.0

The task advances synchronized source version fields to `2.2.0`, adds accepted
notes only under `## Unreleased`, runs `python3 scripts/release.py check-source`,
and forbids dated release headings, release commits, tags, publication,
installation, deployment, restart, and connector actions.
