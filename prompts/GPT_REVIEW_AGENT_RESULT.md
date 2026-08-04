# GPT: Review Local-Agent Result

Load the workflow pinned by `.gpt-workflow.lock`.

Review the submitted branch, commit, archive, diff, agent report, and test evidence
against the task behavior contract and patch specification.

Check scope, behavior, architecture, security, dependencies, tests, skipped gates,
warnings, and every documented or undocumented deviation.

Before declaring `MERGE_READY` for a release-surface task, require exactly one
explicit lifecycle declaration (`implementation_unreleased` or
`release_publication`), its mode-specific state gate, and successful conformance
of the attached project's `scripts/release.py` against the planner canonical script.
`implementation_unreleased` requires `check-source`;
`release_publication` requires `prepare`, then `check-release-ready` to validate
the prepared diff before `commit`, and `check-tag-ready` before tagging. Do not
treat a declaration without its
matching state gate or two-script project conformance result as merge-ready.
The conformance gate must bind both `scripts/release.py` and
`scripts/check-github-ci.py`; CI gates must use `--sha-from-git HEAD`.

For an integrated release/publication task, independently load and validate the
project's explicit `release-publication.json` with
`python3 scripts/validate-release-publication.py <PROJECT>/release-publication.json --repo <PROJECT>` before accepting immutable gates
or `MERGE_READY`. Reject mode/workflow/proof contradictions, including a
`workflow: null` declaration with active CI proofs, an active workflow without
the required distinct-run proof, or release/assets claims that disagree with
the declaration. In `github_actions` mode reject local `gh`, curl, wget,
`GH_TOKEN`, `GITHUB_TOKEN`, or credential/publication commands; only the
declaration-bound read-only verifier is valid.

When corrections are required, produce an Executable Correction Patch Pack with
exact files, code, regression tests, fixtures, application order, and verification gates.

## Select the explicit execution mode

Read `.gpt-workflow.lock` and follow exactly one branch. The mode is never
inferred or combined.

### `gpt_tunnel_managed`

For `gpt_tunnel_managed`, write only the exact canonical `completion.json` and
invoke gateway finalization. Do not write `agent-result.json`, `AGENT_RESULT.md`,
repository evidence, or an evidence-only commit. Use positional `G1..Gn` gate
and `AC1..ACn` acceptance IDs; include no raw commands or duplicated repository
facts. For `repository_evidence`, use the separate repository evidence
workflow and do not write tunnel completion.

### `repository_evidence`

Review the committed v2 manifest and compact evidence JSON, implementation
diff, requirement proofs, captured gate results, deviations, exact
evidence-only diff, and external Git/CI metadata. Do not require a
self-referential evidence commit field and do not rerun runtime gates.

Treat implementation CI in committed evidence separately from final-head CI.
Final evidence-head and PR-head runs are external GitHub/PR metadata and must
not be required as self-referential committed evidence gates. The repository
evidence pair is the only repository-side authority in this mode.
