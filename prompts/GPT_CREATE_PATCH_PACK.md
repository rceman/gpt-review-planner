# GPT: Create GPT Patch Pack v1

Read `docs/GPT_PATCH_PACK_V1.md`, `docs/AGENT_REPORTING.md`,
`docs/PATCH_PACK_HANDOFF.md`, and
`docs/COMPATIBILITY_AUTHORIZATION.md`.

GPT authors architecture, behavior, fixtures, tests, implementation, the
full-index binary patch, requirements, gates, task, and static validation.
The local agent restores dependencies, runs the standard runner, executes
runtime gates, creates implementation/evidence commits, and performs only
narrow integration repairs.

The approved scope is locked before pack creation. Generated task instructions
and reports use the repository's English communication contract.

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

Create only GPT Patch Pack v1 with
`scripts/build-gpt-patch-pack-v1.py`. Do not manually assemble archives, ship
overlays or anchor transforms, create reader scripts, or retain legacy formats.
