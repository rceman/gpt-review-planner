# Committed Agent Evidence

Repository-evidence mode retains separate implementation and evidence commits.
GPT Patch Pack v2 tunnel mode does not create repository evidence or an
evidence-only commit; its only terminal artifact is canonical `completion.json`.

For v2 repository-evidence packs, `gpt_patch_pack_common.py` is the shared
manifest validator used by the builder, runner, standalone pack validator, and
the evidence generator/verifier. The manifest's exact gate argv, environment,
timeout, and output bound are authoritative; evidence is accepted only when
the captured gate run matches those fields and reports exit code zero.

The evidence directory is declared by the pack and contains exactly
`manifest.json` and `evidence.json`. The manifest is copied byte-for-byte from
the pack.

Evidence must include requirement proofs, ordered passing gates, deviations,
and:

```json
{
  "compatibility_scope": "none",
  "compatibility_authorized": false,
  "compatibility_features_added": [],
  "legacy_paths_added": [],
  "fallbacks_added": [],
  "migration_behavior_added": []
}
```

Without explicit authorization every compatibility array is empty. A gate
failure that appears to require compatibility must produce
`BLOCKED_UNAUTHORIZED_COMPATIBILITY_CHANGE`, not a shim or deviation.

Use `generate-agent-evidence.py`, then verify before and after the evidence-only
commit with `verify-agent-evidence.py`. The evidence commit directly follows the
implementation commit and changes exactly the two evidence files.

A missing required runner is an environment failure, never a passing gate. Do
not record `status: pass` while stating that a required tool was unavailable;
restore the prerequisite or stop before creating committed evidence.
# Workflow 2.0.0 authority boundary

The project lock's explicit `execution_mode` controls evidence ownership.
`gpt_tunnel_managed` forbids `.gpt-review/evidence`, repository
`AGENT_RESULT.md`, repository evidence JSON, and evidence-only commits. The
agent writes one compact `completion.json` and invokes gateway finalization.
`repository_evidence` retains one canonical repository evidence authority and
forbids tunnel completion. The mode is required and is never inferred.

The old `agent-result.json`/gateway-agent-result-v2 contract is historical
1.5.0 material only; workflow 2.0.0 has no parallel reader or compatibility
path. Internal raw gate captures remain authoritative for execution integrity,
but are not duplicated in tunnel completion.

## Runtime policy evidence

Runtime-upgrade evidence preserves the single workflow-v2 completion authority.
Record source and target identity, persisted-state scope, explicit migration
authorization, target-decoder-before-activation order, installed and running
version proofs, unchanged-process identity, readiness, protocol/MCP schema
parity, rollback proof, and the durable plan revision after incident closure.
A direct-session receipt is transport evidence only and never a task, run, plan,
Git, merge, or release authority. Do not claim success while a required
activation side effect remains pending.
