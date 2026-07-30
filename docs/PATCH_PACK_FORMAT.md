# GPT Patch Pack v1 Format

[`GPT_PATCH_PACK_V1.md`](GPT_PATCH_PACK_V1.md) is normative.

The only supported executable format is one deterministic `.tar.gz` archive
with one root, strict `MANIFEST.json`, relocatable `SHA256SUMS`,
`AGENT_TASK.md`, and `payload/changes.patch`.

Build with `scripts/build-gpt-patch-pack-v1.py`. Verify and apply with
`scripts/gpt-patch-pack-runner-v1.py`. The runner validates in detached
worktree A, generates a full-index binary patch, replays it in detached
worktree B, verifies the exact target tree, and touches the real checkout only
with explicit `--apply`.

The manifest declares disjoint created, modified, and deleted paths. Rename is
deleted old path plus created new path. Copy is created new path.

Compatibility requires explicit authorization under
`COMPATIBILITY_AUTHORIZATION.md`. Without authorization, legacy formats,
automatic detection, migration, aliases, adapters, fallbacks, and dual paths
are rejected.
