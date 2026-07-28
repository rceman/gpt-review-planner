# Patch-Pack Handoff Contract

This is the normative delivery contract for actionable GPT workflow responses.
The final top-level section is always `## AGENT_HANDOFF`, and no prose may
follow it.

## Response modes

- `manual-download` prints exactly one `PATCH_PACK_NAME` marker followed
  immediately by the exact archive basename, then exactly one
  `SHA256_FILE_NAME` marker followed immediately by the exact sidecar basename.
- `gateway-task-bundle` uses the transport-neutral sentence `Execute the
  materialized patch pack using AGENT_HANDOFF.md.`; the planner does not define
  bus paths or bundle transport.
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

## Agent communication language

Every generated `AGENT_PROMPT.md` MUST be written in English.

All local-agent-facing communication MUST be written in English regardless of
the language used by the owner when communicating with GPT. Every generated
`AGENT_HANDOFF.md` MUST be written in English, and every local-agent question,
progress update, blocker, deviation, gate report, CI report, and final report
must also be written in English.

Agent-facing handoffs MUST NOT duplicate instructions bilingually. Exact
filenames, commands, identifiers, error messages, source excerpts, localized
product content, and other repository-controlled literals may remain in their
original language inside otherwise English instructions. Follow
[`AGENT_COMMUNICATION_LANGUAGE.md`](AGENT_COMMUNICATION_LANGUAGE.md).

Every merge-oriented prompt-only handoff must include the complete post-merge
[`POST_MERGE_BRANCH_CLEANUP.md`](POST_MERGE_BRANCH_CLEANUP.md) sequence in the
same `AGENT_HANDOFF` copy-ready prompt: exact merge-SHA checks, feature-tip ancestry and
identity checks, `git push origin --delete <FEATURE_BRANCH>`, prune, and final
verification. Its report must require `MERGE_FINALIZED` or
`MERGE_CLEANUP_BLOCKED`; the handoff is not complete until those cleanup and
report instructions are included.

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
Every pack must first pass `scripts/validate-patch-pack.py` in text and JSON
modes. `AGENT_HANDOFF.md` is mandatory and its manifest identity must match.
It must contain byte-identical copies of `scripts/patch_pack_scope.py` and
`scripts/verify-agent-evidence.py`, plus the canonical
`scripts/verify-agent-result.sh`, from the exact pinned planner checkout.
Wrappers, proxies, and shims are forbidden. The validator runs all bundled tools
with `--help`, catching top-level startup errors before delivery. A
representative fixture and final response must be validated before handoff.

GPT performs static and artifact validation only; executable quality gates are
owned by the local coding agent and are not claimed as GPT results.
When remote CI is unavailable or intentionally disabled, mandatory local runtime gates remain authoritative. Use `scripts/check-github-ci.py` for exact-SHA observations when policy permits or requires them.
