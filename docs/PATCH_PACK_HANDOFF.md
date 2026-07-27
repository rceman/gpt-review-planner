# Patch-Pack Handoff Contract

This is the normative delivery contract for actionable GPT workflow responses.
The final top-level section is always `## AGENT_HANDOFF`, and no prose may
follow it.

## Response modes

- Patch-pack mode prints plain-text `PATCH_PACK_NAME`, the exact archive
  basename, `SHA256_FILE_NAME`, and the exact sidecar basename.
- Prompt-only mode identifies the prompt and immutable workflow pin, and does
  not claim that an archive was created.
- No-action mode states the reason and does not invent an archive, checksum, or
  execution result.

For schema-v2 packs, `manifest.patch_id` is the sole naming source:
`<patch_id>.tar.gz` and `<patch_id>.tar.gz.sha256`. The final patch-pack
handoff is exactly:

```text
## AGENT_HANDOFF

Apply patch pack `<patch_id>.tar.gz` from the Downloads folder.
```

## Canonical pack checks

Every delivered pack must pass `scripts/validate-patch-pack-delivery.py`.
It must contain byte-identical copies of `scripts/patch_pack_scope.py` and
`scripts/verify-agent-evidence.py` from the exact pinned planner checkout.
Wrappers, proxies, and shims are forbidden. The validator runs both bundled
tools with `--help`, catching top-level startup errors before delivery. A
representative fixture and final response must be validated before handoff.

GPT performs static and artifact validation only; executable quality gates are
owned by the local coding agent and are not claimed as GPT results.
