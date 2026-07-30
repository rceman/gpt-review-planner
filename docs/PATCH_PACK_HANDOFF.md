# GPT Patch Pack v1 Handoff

The archive basename is `<patch_id>.tar.gz`; its sidecar is
`<archive>.sha256` and contains exactly `<sha256>  <archive-basename>`.

`AGENT_TASK.md` is the only instruction inside the archive. `AGENT_PROMPT.md`,
reader scripts, alternate runners, and repository/branch selectors are
forbidden.

Canonical invocation:

```bash
python3 /pinned/planner/scripts/gpt-patch-pack-runner-v1.py   --archive /path/<patch_id>.tar.gz   --archive-sha256 <sha256>   --repo /path/to/repository   --apply
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
