# GPT: Review Local-Agent Result

Load the workflow pinned by `.gpt-workflow.lock`.

Review the submitted branch, commit, archive, diff, agent report, and test evidence
against the task behavior contract and patch specification.

Check scope, behavior, architecture, security, dependencies, tests, skipped gates,
warnings, and every documented or undocumented deviation.

When corrections are required, produce an Executable Correction Patch Pack with
exact files, code, regression tests, fixtures, application order, and verification gates.

## JSON evidence review contract

Review the committed manifest and compact evidence JSON, implementation diff, requirement proofs, gate results, deviations, exact evidence-only diff, and external Git/CI metadata. Do not require a self-referential evidence commit field and do not rerun runtime gates.

Treat implementation CI in committed evidence separately from final-head CI.
Final evidence-head and PR-head runs are external GitHub/PR metadata and must
not be required as self-referential committed evidence gates.
# Workflow 2.0.0 tunnel completion

For `gpt_tunnel_managed`, write only the exact canonical `completion.json` and
invoke gateway finalization. Do not write `agent-result.json`, `AGENT_RESULT.md`,
repository evidence, or an evidence-only commit. Use positional `G1..Gn` gate
and `AC1..ACn` acceptance IDs; include no raw commands or duplicated repository
facts. For `repository_evidence`, use the separate repository evidence
workflow and do not write tunnel completion.
