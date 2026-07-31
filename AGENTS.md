<!-- BEGIN GPT-REVIEW-PLANNER -->
> [!IMPORTANT]
> Before substantial planning, implementation, review, or correction work,
> load the external workflow pinned by [`.gpt-workflow.lock`](./.gpt-workflow.lock).
>
> Canonical repository: [`https://github.com/rceman/gpt-review-planner`](https://github.com/rceman/gpt-review-planner)
>
> Pinned workflow document:
> [`GPT_REVIEW_PLANNER.md`](https://github.com/rceman/gpt-review-planner/blob/01acb488a20689069d07b83ac43e8874a85d7e6b/GPT_REVIEW_PLANNER.md)
>
> Pinned workflow: `v2.0.0` at commit `01acb488a20689069d07b83ac43e8874a85d7e6b`
> Execution mode: `repository_evidence` (explicit; no autodetection or fallback)
>
> Attached code-project reviews default to:
> [`prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md`](https://github.com/rceman/gpt-review-planner/blob/01acb488a20689069d07b83ac43e8874a85d7e6b/prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md)
> Review-only mode is used only when explicitly requested:
> [`prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md`](https://github.com/rceman/gpt-review-planner/blob/01acb488a20689069d07b83ac43e8874a85d7e6b/prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md)
> Archive preparation uses the pinned official tooling and prompt:
> [`prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md`](https://github.com/rceman/gpt-review-planner/blob/01acb488a20689069d07b83ac43e8874a85d7e6b/prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md)
> Archive guide: [`docs/PROJECT_ARCHIVE_REVIEW.md`](https://github.com/rceman/gpt-review-planner/blob/01acb488a20689069d07b83ac43e8874a85d7e6b/docs/PROJECT_ARCHIVE_REVIEW.md)
> Release process: [`docs/RELEASE_PROCESS.md`](https://github.com/rceman/gpt-review-planner/blob/01acb488a20689069d07b83ac43e8874a85d7e6b/docs/RELEASE_PROCESS.md)
>
> If `engineering-profile.json` is present, validate it with the exact pinned
> planner checkout and follow the selected profile and relevant documents.
> Owner instructions win; apply exceptions narrowly and report policy conflicts
> instead of silently selecting another stack. Prefer Rust/Axum for new backend
> components; use Go/Gin only when selected or approved. Production Node.js
> backends and direct frontend database access are forbidden. PostgreSQL schema
> authority remains Liquibase. Python rules apply to tools/tests; a valid legacy
> Python exception does not demand rewrite.
>
> Any release, version bump, or version-tag request requires reading the exact commit-pinned release process.
> The owner explicitly selects the target version.
> Only repository release automation may modify synchronized version files; manual version synchronization is forbidden.
> Operating model:
> - GPT owns architecture, behavior contracts, fixtures, tests, review, and the principal implementation.
> - The local agent owns integration, dependency restoration, compilation, runtime tests, and minimal integration corrections.
> - The local agent must not redesign approved behavior or weaken tests and acceptance criteria.
> - Do not hand-author `.gpt-workflow.lock`; use the pinned preparation prompt and official setup/update tooling.
> - GPT performs only static validation and does not execute runtime quality gates. GPT still authors the approved implementation, fixtures, and tests.
> - The local agent owns runtime integration and gates.
> - Release-commit CI must pass before tagging; final tag CI is external metadata.
> - Do not publish a GitHub Release without explicit authorization.
> - Never force-push or use broad `git push --tags`.
<!-- END GPT-REVIEW-PLANNER -->

