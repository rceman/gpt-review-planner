# Agent Prompt: State Reconciliation

Inspect immutable history separately from mutable operational state. Validate that every configured active project has a durable active project and canonical current plan; every dispatched task has exactly one run; every run references an existing task; active task/run records are non-terminal; and history-only runs are never active.

Use an exact dry-run first. Do not rewrite historical records to satisfy current pointers and do not fabricate a completion. Apply the bounded reconciliation atomically, verify the state graph, and record the durable plan update required by `docs/PERSISTED_STATE_MIGRATION_POLICY.md`.
