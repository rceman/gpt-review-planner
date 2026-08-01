# Agent Prompt: Runtime Upgrade

Execute one declared runtime upgrade as a transaction. Load `docs/RUNTIME_UPGRADE_POLICY.md` and validate the task with `python3 scripts/validate-runtime-upgrade-task.py <TASK_JSON> --repo <REPO> --authoritative-ref <AUTHORITATIVE_REF>` before mutation.

1. Inspect the complete task/run/plan/project graph, source and target identity, installed and running versions, process identities, persisted-state scope, configuration, artifacts, and rollback source.
2. Prepare the target runtime and perform the declared dry-run migration. Back up the exact declared state.
3. Run target-decoder validation before shutting down the old runtime. Do not activate while migration or decoder validation is pending.
4. Activate only the declared affected process. Prove that every declared unchanged process retained its PID/executable identity.
5. Verify installed version, running version, readiness, health, protocol/MCP tool input and output schemas, and rollback evidence.
6. Report `succeeded` only when the exact success criterion is complete. Otherwise report `failed` or `needs_gpt_revision` through the canonical completion authority and execute rollback when the trigger requires it.

Do not use detached continuation as a second authority, do not claim a preparation-only task is a full upgrade, and do not hide incomplete side effects in remaining risks.
