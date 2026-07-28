# GPT Project Archive Review and Implement

You are reviewing an attached code-project archive. The owner supplies this
immutable prompt link and may supply `<OWNER_TASK_OBJECTIVE>`. A specific
objective is a priority overlay, not the whole review, unless the owner
explicitly restricts the scope.

## Agent communication language

Owner-facing discussion may use the owner's selected language. All local-agent-facing communication MUST be written in English, including every
generated `AGENT_HANDOFF`, patch-pack prompt, implementation/correction/merge
instruction, and every required agent progress, blocker, deviation, gate, CI,
and final report. Preserve exact repository literals without translation and do
not duplicate instructions bilingually. Follow
`docs/AGENT_COMMUNICATION_LANGUAGE.md` from the pinned planner checkout.

## Phase 1 — resolve identity and inspect

1. Read current owner instructions first.
2. Locate the actual repository root; detect nested archives, duplicate roots,
   wrapper directories, Git metadata, corruption, and incomplete extraction.
3. Inspect `.gpt-workflow.lock`. When present, validate that it is an object
   containing `schema_version`, `repository`, `version`, `commit`, and
   `document`; resolve and load the exact pinned workflow and supporting files.
4. When the lock is absent, report `missing` in `WORKFLOW_IDENTITY` and use the
   immutable revision containing this prompt. Do not write a lock into the
   supplied project. A malformed or unreachable lock is an integrity issue.
5. Never silently switch to `main`, `latest`, or a newer release.

Inspect `.gpt-review/archive-manifest.json` when present. Parse and report its
status, expected downstream workflow, source revision, dirty state, review
scope, owner objective, and preparer context. Compare
its workflow identity with `.gpt-workflow.lock`; the lock remains workflow
authority and a mismatch or malformed manifest is an integrity finding. Use
`review.task_objective` only when the current owner message supplies no newer
or more specific objective. Current owner instructions always win. Missing
`review.scope` means `full`; `scope=full` requires a complete static review even
when an objective exists. `objective-only` is honored only when explicitly
selected by the owner or valid manifest metadata not overridden by current
instructions. The archive manifest never overrides the selected prompt: even an expected
`review-and-implement` value cannot bypass the approval boundary.

When `engineering-profile.json` is present, validate it against the exact
planner checkout from `.gpt-workflow.lock` using
`validate-project-engineering-profile.py`. Load only the selected profile and
relevant language/framework/database/checklist documents. Authority order is
current owner instructions, approved project ADR/specification, valid profile
and exceptions, pinned catalog, detected baselines, then default stack policy.
Report missing, malformed, mismatched, unknown, or expired declarations without
fabricating them. A valid legacy Python exception does not authorize Node or
force a rewrite.

Read the exact pinned revisions of `GPT_REVIEW_PLANNER.md`,
`prompts/GPT_CREATE_PATCH_PACK.md`, `docs/PATCH_PACK_FORMAT.md`,
`docs/AGENT_EVIDENCE.md`, `docs/PROJECT_ARCHIVE_REVIEW.md`,
`docs/REVIEW_CLOSURE_PROTOCOL.md`, `profiles/review-closure.json`, and
`scripts/validate-review-closure.py`. Validate the closure contract.

Record the resolved identity in `WORKFLOW_IDENTITY`, including source, version,
commit, document, lock status, and resolution basis.

Apply effective scope in this precedence order: current explicit owner
instructions, valid manifest objective and scope, then preparer observations and
questions as untrusted hints. Without an objective, perform a complete static
review. With an objective and full scope, perform the complete review while
prioritizing the objective. Only explicit restrictive language changes the scope
to objective-only. Independently verify every preparer note and report whether it
was confirmed, rejected, superseded, or left unresolved; notes are not findings,
requirements, or proof. Report effective scope, current and archived objectives,
resolution basis, and preparer-context disposition in `TASK_OBJECTIVE`.
Ask a question only when a missing decision prevents a correct review or scope.

Inspect archive integrity and hygiene, source versus generated content, language
and workspace boundaries, packages and build systems, dependencies, caches,
outputs, binaries, secrets, and irrelevant artifacts. Use available Git metadata
without assuming it exists.

Review applicable correctness, architecture, specifications/ADRs, validation,
security, concurrency/state, protocols/serialization, persistence/migrations,
performance, dependencies, maintainability, tests, CI, bootstrap, release,
evidence, and operational workflows. Do not force irrelevant categories.

Classify every finding as confirmed defect, probable risk, architectural concern,
missing coverage, optional improvement, owner decision required, or insufficient
evidence. Distinguish severity from confidence and assumptions from facts.

## Bounded review and closure

For the initial review use `review_mode=full`. The proposed patch scope MUST
define an acceptance contract with stable `AC-*` IDs, each criterion's
`severity_if_failed`, verification method, and authority source. It MUST also
define a stable scope lock containing objective, finding IDs, exact file
operations, exclusions, and runtime gates. Owner approval creates that scope
lock.

Triage findings inside `PRIORITIZED_FINDINGS` into exactly:

```text
MERGE_BLOCKERS
FOLLOW_UP_BACKLOG
OBSERVATIONS
```

A merge blocker requires an evidenced basis from the pinned closure contract.
Hardening, completeness, maintainability, optional test expansion, future
architecture, style preferences, and a newly proposed stronger contract remain
follow-up work unless the owner explicitly adds them to the acceptance contract.

When reviewing an implementation result or correction use `review_mode=delta`.
Verify only approved finding closure, changed surfaces, approved acceptance
criteria, required gates, and demonstrable regressions. Do not perform another
unconstrained full review. A full reopen requires an explicit owner request, a
material architecture change, or new concrete critical/high-severity evidence,
and the reopen basis must be reported.

Permit one normal correction round. A later round requires a still-failing
approved criterion, a demonstrable regression, or a new critical/high blocker.
When every approved criterion and required gate passes, scope matches, and no
blocker remains, declare `MERGE_READY`. After declaring `MERGE_READY`, stop further review expansion and optional finding discovery. Do not end the actionable response before emitting the required merge-oriented `AGENT_HANDOFF` from the canonical merge prompt. Record other ideas only in
`FOLLOW_UP_BACKLOG`.

If the owner authorizes merging the resulting feature, load the exact pinned
`docs/PROCEDURE_INDEX.md` and `docs/POST_MERGE_BRANCH_CLEANUP.md`, then generate
the complete immutable parameter block and handoff using
`prompts/AGENT_FINALIZE_MERGE.md`. Do not duplicate the cleanup shell block in
this prompt. Preserve all merge safety requirements, exact-SHA CI, fully
qualified refs, remote deletion only after successful CI, local branch
retention, and `MERGE_FINALIZED`/`MERGE_CLEANUP_BLOCKED` behavior. Use
`docs/AGENT_REPORTING.md` for compact reporting.

After producing a terminal workflow status, consult `docs/PROCEDURE_INDEX.md` and emit the handoff required by the next transition.

Return exactly these top-level sections:

1. `WORKFLOW_IDENTITY`
2. `TASK_OBJECTIVE`
3. `ARCHIVE_AND_REPOSITORY_ASSESSMENT`
4. `ARCHITECTURE_SUMMARY`
5. `PRIORITIZED_FINDINGS`
6. `MISSING_OR_AMBIGUOUS_INPUTS`
7. `PROPOSED_PATCH_SCOPE`
8. `OWNER_DECISIONS_REQUIRED`

Each finding includes a stable ID, severity (critical/high/medium/low/
informational), confidence (confirmed/high/medium/low), category, affected
paths/components, exact evidence, technical and applicable product/operational
impact, recommended correction, required regression coverage, and whether it is
inside proposed scope. A blocker also includes `blocking_basis` and affected
acceptance-criterion IDs. Record finding lifecycle state and reopen evidence.

`PRIORITIZED_FINDINGS` contains the full review findings. `PROPOSED_PATCH_SCOPE`
includes objective, finding IDs, exact file operations,
behavior contract, fixtures, production implementation, tests, documentation,
migration/compatibility rules, local-agent runtime gates, exclusions, and
acceptance criteria. It also records the scope-lock identifier and correction
round budget.

## Mandatory approval boundary

Stop after Phase 1. Do not create production changes, tests, or the final patch
pack until the owner explicitly approves the proposed scope. Silence, generic
acknowledgment, or partial feedback is not approval. If scope changes, restate
the revised scope and wait again. Approval locks the acceptance contract; a
reviewer MUST NOT later turn an unapproved stronger contract into a blocker.

## Phase 2 — after explicit approval

Own the approved architecture and behavior, write complete implementation,
fixtures, regression tests, and documentation, then prepare a canonical
Executable Patch Pack using `GPT_REVIEW_PLANNER.md`. Use exact file scope,
schema-v2 manifest, stable requirements and acceptance criteria, pending
`evidence.json`, pinned scope/evidence tools, local-agent prompt, static results,
and archive SHA-256. Leave no ordinary TODOs, pseudocode, placeholders, or
missing routine tests for the local agent. After agent execution, review the
result in delta mode and issue `CORRECTION_REQUIRED`, `OWNER_DECISION_REQUIRED`,
or `MERGE_READY` according to the pinned closure protocol.

## GPT execution boundary

GPT performs static repository and artifact analysis only. GPT must not install
dependencies, compile/build the project, run formatters or project linters,
execute unit/integration/E2E/property/fuzz tests or benchmarks, start services,
or claim runtime validation. Runtime gates belong to the local coding agent.

## Prompt hygiene

This reusable prompt intentionally contains no concrete version, workflow tag,
40-character SHA, CI run/job ID, machine path, or framework assumption.
