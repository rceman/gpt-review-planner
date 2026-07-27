# Patch-Pack Handoff Contract

This is the normative delivery contract for actionable GPT workflow responses.
The final top-level section is always `## AGENT_HANDOFF`, and no prose may
follow it.

## Response modes

- Patch-pack mode prints exactly one `PATCH_PACK_NAME` marker followed
  immediately by the exact archive basename, then exactly one
  `SHA256_FILE_NAME` marker followed immediately by the exact sidecar basename.
- Prompt-only mode ends with a complete copy-ready local-agent prompt.
- No-action mode ends with the exact no-action sentence below.

For schema-v2 packs, `manifest.patch_id` is the sole naming source:
`<patch_id>.tar.gz` and `<patch_id>.tar.gz.sha256`. The final patch-pack
handoff is exactly:

```text
## AGENT_HANDOFF

Apply patch pack `<patch_id>.tar.gz` from the Downloads folder.
```

Prompt-only mode must end exactly with this structure, with no prose or section
after `AGENT_HANDOFF`:

```text
## AGENT_HANDOFF

<complete copy-ready local-agent prompt>
```

The prompt must include the repository, local repository when known, branch,
exact base or expected HEAD, exact required actions, runtime gates, constraints,
and the required final report.

No-action mode must end exactly with this text, with no prose or section after
`AGENT_HANDOFF`:

```text
## AGENT_HANDOFF

No agent action is required. Preserve the reported state and wait for the next owner instruction.
```

For every mode, `## AGENT_HANDOFF` is the final top-level section and no
non-whitespace content may follow it.

## Canonical pack checks

Every delivered pack must pass `scripts/validate-patch-pack-delivery.py`.
It must contain byte-identical copies of `scripts/patch_pack_scope.py` and
`scripts/verify-agent-evidence.py` from the exact pinned planner checkout.
Wrappers, proxies, and shims are forbidden. The validator runs both bundled
tools with `--help`, catching top-level startup errors before delivery. A
representative fixture and final response must be validated before handoff.

GPT performs static and artifact validation only; executable quality gates are
owned by the local coding agent and are not claimed as GPT results.
