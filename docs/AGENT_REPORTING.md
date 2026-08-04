# Agent Reporting Contract

## Bounded agent execution

Use one exact-SHA CI helper invocation with `--wait`; manual sleeps and duplicate
polling are prohibited. Use one script-managed detached worktree and remove it
after execution. Rely on subprocess exit status, bounded timeouts, and
structured gate-run, CI, and evidence JSON. Do not use routine `ps`, repeated
`ls` or `cat`, one-off JSON readers, or manually synchronize counts, SHAs, URLs,
scope, summaries, or proof hashes.

Prepare proof selectors before publication and complete the local pipeline
preflight before pushing. Committed evidence is immutable; stale uncommitted
attempts are disposable only after validation and quarantine, never overwrite or
reuse them. A blocker contains only phase, stable reason, bounded diagnostic,
preserved state, and the exact next action.

The model decides semantics.
Automation executes mechanics.
Generated artifacts carry machine facts.
The agent does not manually synchronize derived data.

When the workflow runner exists, the agent provides one semantic task specification
and invokes only `run --task` or `resume`. The
agent must not invoke underlying CI, gate, preparation, evidence, verification,
commit, or reporting helpers manually. Use `scripts/run-agent-evidence-workflow.py run` for the complete
evidence lifecycle and `resume` for interruption recovery. Agents invoke
workflows. Scripts execute phases. Structured state carries progress. Models do
not manually orchestrate deterministic shell pipelines.

## Gateway-managed terminal reporting

For a gateway-managed GPT task, the interactive Airelay/Codex response is only
an execution log. It is never the terminal report. The agent writes one strict
`completion.json` to the gateway-authoritative path and invokes gateway
finalization for `succeeded`, `needs_gpt_revision`, or `failed`.

Do not manually repeat repository, project, branch, timestamps, bundle digest,
worktree checks, remote-head checks, or bus publication metadata. The finalizer
derives and validates those facts. The agent records only the canonical
completion fields and positional gate/acceptance identities.

Do not ask the owner for approval or clarification. Finalize the blocker through
the gateway. If a model turn ends without finalization, the gateway may issue one
bounded corrective reprompt and then publish a synthetic failed result.

This contract is the human/GPT projection of machine-verifiable execution evidence.

1. Report each fact once.
2. Omit raw command output when a concise result is sufficient.
3. Do not repeat values already in a canonical record.
4. Preserve exact error output for failures and diagnostics.
5. Group test counts by gate.
6. Keep full logs in the execution environment unless needed to explain failure.
7. Committed evidence remains authoritative and is not replaced by a summary.

For successful CI, emit exactly one compact record:

```text
Merge CI: success | sha=<SHA> | run=<RUN_ID> | job=<JOB_ID_OR_NULL> | run_url=<RUN_URL> | job_url=<JOB_URL_OR_NULL>
```

Use `Implementation CI`, `Evidence CI`, `Merge CI`, `Release CI`, or `Tag CI` as appropriate. Do not repeat state, blocking, policy, repository, IDs, URLs, checked SHA, status, or conclusion after the record. Successful helper JSON is not pasted before repeated fields.

For failure, use one record such as:

```text
Merge CI: failed | blocking=true | sha=<SHA> | run=<RUN_OR_NULL> | job=<JOB_OR_NULL> | exit=<EXIT_CODE> | message=<DETERMINISTIC_MESSAGE>
```

Raw JSON is included once only for blocking, invalid, internally inconsistent, diagnostically important unavailable results, or explicit owner request. Permitted absence is reported as `Implementation CI: no_run | blocking=false | policy=auto | sha=<SHA> | message=<SUMMARY>` and is never called success.

Final reports normally contain terminal status, identity, changed scope, grouped gates, one CI record per observed SHA, evidence identity, final Git/ref/worktree state, and prohibited-operation confirmation. Machine evidence must retain all required fields in manifests, evidence, schemas, and helper output.
# Workflow 2.0.0 completion projection

For `gpt_tunnel_managed`, write exactly one completion object with
`schema_version`, `run_id`, `task_sha256`, `status`, `summary`, ordered
`gate_results`, ordered `acceptance_coverage`, `deviations`, and
`remaining_risks`. Use `G1..Gn` and `AC1..ACn` positionally. Do not paste raw
commands, full acceptance text, branch/HEAD facts, evidence paths, or a second
agent-result/evidence object. The gateway hub report is the only second-side
authority, and it is gateway-owned rather than agent-authored.

For `repository_evidence`, use the existing two-file repository evidence
contract and do not produce tunnel completion. Agents invoke workflows; scripts
execute phases; structured state carries progress; models do not manually
orchestrate deterministic shell pipelines.

## Runtime upgrade and incident projection

Runtime reports must distinguish installed version from running version and include the exact source/target identity, migration/decoder ordering, affected and unchanged process proof, readiness, protocol/MCP parity, rollback state, and the durable plan revision after incident closure. Do not report a full upgrade as succeeded while activation or a required side effect is pending, and do not use `remaining_risks` to hide incomplete work.

Incident reports use one bounded record containing the trigger, startup phase, exact first fatal line, competing hypotheses, source/log/state correlation, and corrective-action checkpoint. A direct-session receipt is transport metadata only and must not be presented as task, run, plan, Git, merge, or release evidence. Tool reports record required names and schema parity rather than a hard-coded tool count.

Release reports also identify the exact lifecycle mode and target version. An
`implementation_unreleased` source-state result is not release-ready and must
not be reported as a release, tag, or publication. Publication reports record
the separate source, release-ready, tag-ready, release-commit, and annotated
tag proofs without claiming a later phase from an earlier successful check.
For integrated projects, publication reports also identify the declared mode,
workflow identity when present, exact tag-push refspec, distinct tag/publication
CI result, and read-only verifier result. Read [`RELEASE_PUBLICATION.md`](RELEASE_PUBLICATION.md);
do not report a GitHub Release or assets when the declaration says `none` or
`tag_only`.

## Separate owner-state reporting

Owner-facing reports keep these states separate and ordered; none may be
collapsed into a generic “release succeeded” claim:

1. implementation merged
2. release commit
3. main
4. tag created
5. tag pushed
6. tag CI
7. auto workflow
8. GitHub Release
9. assets
10. installed version
11. running version
12. activated
13. connector refresh

Each state records its own status and identity. A later state cannot be inferred from an earlier one: a successful release commit does not prove main, tag creation does not prove tag push or tag CI, an auto workflow does not by itself prove a GitHub Release or assets, and installed version, running version, activation, and connector refresh remain separate operational checks.
