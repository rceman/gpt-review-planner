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

No-action mode must end exactly with this text, with no prose or section after
`AGENT_HANDOFF`:

```text
## AGENT_HANDOFF

No agent action is required. Preserve the reported state and wait for the next owner instruction.
```

For every mode, `## AGENT_HANDOFF` is the final top-level section and no
non-whitespace content may follow it.

## Gateway terminal-output contract

Every executable `AGENT_HANDOFF.md` contains `## TERMINAL_OUTPUT_PROTOCOL`.
For future gateway-managed tasks it must state that:

1. the interactive session response does not complete the task;
2. the agent writes only the strict gateway-authoritative `agent-result.json`;
3. the agent runs the exact generated `complete-task` command;
4. the command is mandatory for `succeeded`, `needs_gpt_revision`, and `failed`;
5. blockers are finalized through the gateway instead of asking the owner;
6. gateway publication and derived Git checks must not be reimplemented as a
   hand-written shell block.

The result schema is `schemas/gateway-agent-result-v2.schema.json` and the
dependency-free semantic validator is
`scripts/validate-gateway-agent-result.py`. Legacy dual-output execution may be
used only by a gateway version that predates the finalizer protocol; newly
generated packs use the JSON-only contract.

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
## Post-merge merge-oriented prompt-only handoff

This post-merge handoff contract governs merge-finalization prompts.

## Bounded agent execution

Before runtime gates or evidence creation, read [`AGENT_REPORTING.md`](AGENT_REPORTING.md)
and follow its bounded rules: one `check-github-ci.py --wait` per SHA, one
detached worktree, structured results, no manual sleeps or routine process
inspection, and no manual synchronization of generated facts. Fresh evidence
attempts are required; stale uncommitted output is not authoritative.

A merge-oriented prompt-only handoff MUST provide complete merge-finalization instructions using exactly one of: complete inline instructions, or the preferred compact reference to `prompts/AGENT_FINALIZE_MERGE.md` from the exact pinned planner checkout or immutable tag/commit URL plus the complete parameter block. Compact reference mode is complete because the agent must load the canonical prompt and linked normative contracts before execution. Mutable `main`, `latest`, or unresolved references are forbidden; a summary must not replace loading the canonical prompt.

Required parameters are `REPOSITORY`, `LOCAL_REPOSITORY`, `SSH_ORIGIN`, `MAIN_BRANCH`, `FEATURE_BRANCH`, `EXPECTED_MAIN_BEFORE`, `EXPECTED_FEATURE_HEAD`, `EXPECTED_VERSION`, `CI_POLICY`, `CI_WORKFLOW`, and `CI_EVENT`. Both modes require exact merge-SHA CI, feature-tip identity and ancestry, remote deletion only after successful CI, pruning, local feature-branch retention, final verification, and `MERGE_FINALIZED`, `MERGE_CLEANUP_BLOCKED`, or pre-merge `MERGE_BLOCKED`. No handoff is required to inline the cleanup sequence when it loads the complete pinned canonical prompt.

After producing a terminal workflow status, consult `docs/PROCEDURE_INDEX.md` and emit the handoff required by the next transition.

Executable packs may use the canonical `gate-plan.json`, `evidence-plan.json`,
and bundled automation scripts to capture runtime gates and generate evidence.
Intermediate logs and helper JSON remain outside committed evidence.
The generator accepts only the declared evidence directory's manifest and
generated evidence file, whether Git reports them individually or as a compact
directory-level untracked entry; it validates the expanded contents.
The agent provides one semantic task specification to the workflow runner.
Runtime state is stored under the Git common directory. Agents invoke workflows;
scripts execute phases; structured state carries progress. Models do not manually
orchestrate deterministic shell pipelines or assemble temporary input directories.
