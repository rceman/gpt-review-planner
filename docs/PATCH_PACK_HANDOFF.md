# GPT Patch Pack v2 Handoff

The archive basename is `<patch_id>.tar.gz`; its sidecar is
`<archive>.sha256` and contains exactly `<sha256>  <archive-basename>`.

`AGENT_TASK.md` is the only instruction inside the archive. `AGENT_PROMPT.md`,
reader scripts, alternate runners, and repository/branch selectors are
forbidden.

Canonical invocation:

```bash
python3 /pinned/planner/scripts/gpt-patch-pack-runner-v2.py \
  --archive /path/<patch_id>.tar.gz \
  --archive-sha256 <sha256> \
  --repo /path/to/repository \
  --apply
```

Before delivery, the builder must complete verify-only execution and the
delivery validator must verify the sidecar. Release changes to the runner,
builder, schema, template, or format docs require the synthetic end-to-end
self-test.

When compatibility is not authorized, `AGENT_TASK.md` contains:

```text
Compatibility scope: none
Compatibility authorization: not granted
Canonical implementation: <single schema/protocol/path>
Legacy behavior: unsupported and out of scope
```
# Workflow 2.0.0 mode binding

Every new GPT Patch Pack v2 declares exactly one `execution_mode`. In
`gpt_tunnel_managed` mode the data-only archive plus pinned runner is the sole
execution path; the handoff requires one `completion.json` and gateway
finalization, and explicitly forbids repository evidence and evidence-only
commits. In `repository_evidence` mode the handoff requires the one canonical
repository evidence directory and forbids tunnel completion. No v1/v2
negotiation, aliases, or fallback readers are exposed for new tasks.

Runtime-affecting patch packs must link the pinned runtime-upgrade, migration,
incident, and tool-contract policies and include the machine-readable task
declaration validated by `scripts/validate-runtime-upgrade-task.py`. The local
agent must prove target-decoder validation before activation, installed versus
running version identity, unchanged-process identity, readiness, protocol/tool
schema parity, and rollback. A handoff must not claim a full upgrade while any
required activation side effect is pending.
