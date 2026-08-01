# Agent Prompt: Persisted-State Migration

Load `docs/PERSISTED_STATE_MIGRATION_POLICY.md`. Verify an explicit owner authorization, exact old/new schemas, bounded record set, direction, dry-run, backup, canonical migration entry point, target decoder, atomic commit, rollback, and removal condition before touching state.

Preserve immutable historical records. Clear obsolete operational references instead of fabricating completion. Never add a permanent dual reader, fallback field alias, fake placeholder record, or manual field deletion when a canonical migration exists. Decode the target state before activation, commit atomically, then verify current project, plan, task, and run invariants. On failure restore the backup and record exact rollback proof.
