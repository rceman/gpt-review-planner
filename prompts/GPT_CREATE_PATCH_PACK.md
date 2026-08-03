# GPT: Create GPT Patch Pack v2

Read `docs/PATCH_PACK_FORMAT.md`, `docs/AGENT_REPORTING.md`,
`docs/PATCH_PACK_HANDOFF.md`, and
`docs/COMPATIBILITY_AUTHORIZATION.md`.

GPT authors architecture, behavior, fixtures, tests, implementation, the
full-index binary patch, requirements, gates, task, and static validation.
The local agent restores dependencies, runs the standard runner, executes
runtime gates, creates implementation/evidence commits, and performs only
narrow integration repairs.

The approved scope is locked before pack creation. Generated task instructions
and reports use the repository's English communication contract.
Agents perform a tool-availability preflight for every required tool before runtime gates.

If the task touches VERSION, configured version fields, CHANGELOG.md, release
metadata, release tooling, or tags, require the exact task-specific
declarations `Release lifecycle mode: implementation_unreleased` or `Release
lifecycle mode: release_publication` and `Release target version: X.Y.Z`.
Require the matching machine-checkable state gate and the exact two-script
`scripts/validate-release-tool-conformance.py` proof for both the project's
`scripts/release.py` and `scripts/check-github-ci.py`; exact CI gates must use
`--sha-from-git HEAD`. Do not allow `MERGE_READY` from a missing or
contradictory lifecycle.

Unless explicitly authorized, declare:

```text
Compatibility scope: none
Compatibility authorization: not granted
Canonical implementation: <single schema/protocol/path>
Legacy behavior: unsupported and out of scope
```

Remove unauthorized shims, fallbacks, old schemas, adapters, migration code,
aliases, negotiation, dual paths, and speculative extension points before
building.

Create only GPT Patch Pack v2 with
`scripts/build-gpt-patch-pack-v2.py`. Do not manually assemble archives, ship
overlays or anchor transforms, create reader scripts, or retain legacy formats.
# Workflow 2.0.0 generated handoff rules

Generated packs must declare one explicit execution mode. Tunnel handoffs must
require only implementation commits, the compact canonical `completion.json`,
and gateway finalization. They must forbid `.gpt-review/evidence`, repository
evidence JSON, `AGENT_RESULT.md`, evidence-only commits, raw command duplication,
and full acceptance-text duplication. Repository-evidence handoffs use the
existing evidence workflow as the single authority. Do not expose v1 as a new
task creation path.
