# GPT Review Project Archive — Review Only

Review the attached archive without implementing it. The owner may supply
`<OWNER_TASK_OBJECTIVE>`; without one, perform a complete static review.

Resolve identity exactly as the primary archive-review prompt requires: read
owner instructions, validate `.gpt-workflow.lock` when present, load its exact
pinned `GPT_REVIEW_PLANNER.md`, `prompts/GPT_CREATE_PATCH_PACK.md`,
`docs/PATCH_PACK_FORMAT.md`, `docs/AGENT_EVIDENCE.md`, and
`docs/PROJECT_ARCHIVE_REVIEW.md`. If the lock is absent, report that status and
use the immutable revision containing this prompt. Never fabricate a lock or
silently use `main`, `latest`, or another mutable ref.

Inspect archive integrity, repository root, nested/wrapper roots, Git metadata,
languages, workspaces, generated content, dependencies, caches, outputs,
secrets, binaries, and relevant source. Focus on the owner objective while
surfacing unrelated critical blockers without broadening implementation scope.

Return these sections:

1. `WORKFLOW_IDENTITY`
2. `TASK_OBJECTIVE`
3. `ARCHIVE_AND_REPOSITORY_ASSESSMENT`
4. `ARCHITECTURE_SUMMARY`
5. `PRIORITIZED_FINDINGS`
6. `MISSING_OR_AMBIGUOUS_INPUTS`
7. `RECOMMENDED_IMPLEMENTATION_ORDER`
8. `INDEPENDENT_PATCH_DECOMPOSITION`
9. `OWNER_DECISIONS_REQUIRED`

Every finding includes stable ID, severity, confidence, category, affected
paths/components, exact evidence, impact, remediation, regression coverage, and
whether it belongs in a possible future scope.

This is analysis-only. Do not modify project files, write production code,
write/change tests. Do not create an Executable Patch Pack or a local-agent prompt,
or run project code, runtime gates, benchmarks, services, or dependencies.
There is no Phase 2 in review-only mode. Stop after findings and decomposition for
owner direction.
