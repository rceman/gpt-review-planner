# Planner v2.1.0 Gateway Integration Handoff

## Immutable identity

- Repository: `rceman/gpt-review-planner`
- Origin: `git@github.com:rceman/gpt-review-planner.git`
- Initial main: `fb55ce752f03cfe13cfddc4babc8930f8983d034`
- Policy implementation: `29587e3d703e0df2f7e6c31a87bd3508af601388`
- Release commit: `07c384c9729f0b397fc7a523ef40422dcec956db`
- Release-tree correction: `900d284a97dd745d079134b49e5654b909e88c0a`
- Tagged release main: `900d284a97dd745d079134b49e5654b909e88c0a`
- Version/tag: `2.1.0` / `v2.1.0`

The single workflow-v2 completion authority remains
`<gateway-state-dir>/runs/<run-id>/completion.json`. Do not add
`result.json`, `evidence.json`, duplicate digests, workflow-v1 finalization, or
permanent compatibility readers.

## Policy and executable surfaces

Read and apply:

- `docs/RUNTIME_UPGRADE_POLICY.md`
- `docs/PERSISTED_STATE_MIGRATION_POLICY.md`
- `docs/INCIDENT_RESPONSE_POLICY.md`
- `docs/DIRECT_AGENT_SESSION_CONTROL_POLICY.md`
- `docs/TOOL_CONTRACT_INTEGRITY_POLICY.md`
- `docs/CHAT_HANDOFF_CHECKPOINT.md`
- `docs/COMPATIBILITY_AUTHORIZATION.md`
- `docs/PROCEDURE_INDEX.md`
- `docs/AGENT_REPORTING.md`
- `docs/RELEASE_PROCESS.md`

Canonical prompts are:

- `prompts/AGENT_RUNTIME_UPGRADE.md`
- `prompts/AGENT_RUNTIME_RECOVERY.md`
- `prompts/AGENT_INCIDENT_DIAGNOSIS.md`
- `prompts/AGENT_PERSISTED_STATE_MIGRATION.md`
- `prompts/AGENT_STATE_RECONCILIATION.md`
- `prompts/AGENT_DIRECT_SESSION_CONTROL_IMPLEMENTATION.md`
- `prompts/AGENT_TOOL_CONTRACT_AUDIT.md`
- `prompts/AGENT_CHAT_HANDOFF.md`
- `prompts/AGENT_RELEASE_VERSION.md`
- `prompts/AGENT_FINALIZE_MERGE.md`

The machine-readable runtime-upgrade declaration is
`templates/runtime-upgrade-task.json`, checked by
`scripts/validate-runtime-upgrade-task.py` against
`schemas/runtime-upgrade-task.schema.json`.

## Required runtime fields and safety rules

Every upgrade declares source/target versions and exact SHAs, persisted-state
scope, migration authorization and entry point, target-decoder validation,
affected and unchanged processes, installed and running version proofs,
readiness, protocol/MCP checks, rollback source/trigger, compatibility scope,
and one exact success criterion. Target decoding and migration occur before old
runtime shutdown. Unchanged process identity is proven before and after. A
preparation-only task cannot claim a full upgrade, and remaining risks cannot
hide a pending side effect.

Incident mode starts after two failed activations, 15 minutes without progress,
installed/running mismatch, unknown readiness cause, rollback failure, graph
inconsistency, or repeated one-blocker-at-a-time discovery. It permits bounded
read-only diagnosis and prohibits blind retry, restart, reinstall, migration,
and bypass chains until the first fatal line, startup phase, hypotheses, and
source/log/state correlation are recorded.

Direct sessions are registered, bounded, serialized transport only. `agent_send`,
`agent_tail`, and `agent_status` must not create tasks/runs/plans or mutate Git
or the repository. Tool releases require live `tools/list`/`tools/call` input and
output schema parity; fixed tool counts are forbidden. History-only runs cannot
be active, dispatched tasks have exactly one run, and active projects require a
valid canonical current plan.

## Gateway integration requirements

The gateway integration must pin:

```text
workflow_repository=https://github.com/rceman/gpt-review-planner
workflow_commit=900d284a97dd745d079134b49e5654b909e88c0a
```

It must verify the authoritative remote branch/ref, not an incidental local
checkout `HEAD`, and must preserve the planner's one completion authority and
push-before-finalize semantics. Gateway release validation must run:

```bash
python3 scripts/validate-runtime-upgrade-task.py templates/runtime-upgrade-task.json
python3 scripts/validate-review-closure.py
python3 scripts/validate-engineering-catalog.py
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s examples/rust-domain-feature/reference/python -v
python3 -m pytest -q
python3 -m compileall -q scripts tests examples
python3 scripts/selftest-gpt-patch-pack-v2.py
python3 scripts/release.py check
git diff --check
```

## Remaining integration and exact next action

The planner-side policy release is complete. Remaining work belongs to the
gateway integration: validate the installed/running gateway and tunnel against
the pinned planner commit, verify MCP input/output schema parity and the live
capability surface, rehearse persisted-state migration and rollback, then run
the joint workflow smoke. Do not modify the planner or gateway source while
merely consuming this handoff. Start the next phase only as a separately
authorized gateway integration task and update the durable planner plan before
dispatching executable work.
