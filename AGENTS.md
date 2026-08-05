<!-- BEGIN GPT-REVIEW-PLANNER -->
> [!IMPORTANT]
> Before substantial planning, implementation, review, or correction work,
> load the external workflow pinned by [`.gpt-workflow.lock`](./.gpt-workflow.lock).
>
> Canonical repository: [`https://github.com/rceman/gpt-review-planner`](https://github.com/rceman/gpt-review-planner)
>
> Pinned workflow document:
> [`GPT_REVIEW_PLANNER.md`](https://github.com/rceman/gpt-review-planner/blob/74059a423d7dd280bd536b91a177bdb12823c879/GPT_REVIEW_PLANNER.md)
>
> Pinned workflow: `74059a423d7dd280bd536b91a177bdb12823c879` at commit `74059a423d7dd280bd536b91a177bdb12823c879`
> Execution mode: `gpt_tunnel_managed` (explicit; no autodetection or fallback)
>
> Attached code-project reviews default to:
> [`prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md`](https://github.com/rceman/gpt-review-planner/blob/74059a423d7dd280bd536b91a177bdb12823c879/prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md)
> Review-only mode is used only when explicitly requested:
> [`prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md`](https://github.com/rceman/gpt-review-planner/blob/74059a423d7dd280bd536b91a177bdb12823c879/prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md)
> Archive preparation uses the pinned official tooling and prompt:
> [`prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md`](https://github.com/rceman/gpt-review-planner/blob/74059a423d7dd280bd536b91a177bdb12823c879/prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md)
> Archive guide: [`docs/PROJECT_ARCHIVE_REVIEW.md`](https://github.com/rceman/gpt-review-planner/blob/74059a423d7dd280bd536b91a177bdb12823c879/docs/PROJECT_ARCHIVE_REVIEW.md)
> Release process: [`docs/RELEASE_PROCESS.md`](https://github.com/rceman/gpt-review-planner/blob/74059a423d7dd280bd536b91a177bdb12823c879/docs/RELEASE_PROCESS.md)
> Release lifecycle: [`docs/RELEASE_LIFECYCLE.md`](https://github.com/rceman/gpt-review-planner/blob/74059a423d7dd280bd536b91a177bdb12823c879/docs/RELEASE_LIFECYCLE.md)
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
> Any release, version bump, or version-tag request requires reading the exact commit-pinned release lifecycle and release process.
> The owner explicitly selects the target version.
> Only repository release automation may modify synchronized version files; manual version synchronization is forbidden.
> Release-surface tasks declare exactly one lifecycle mode and target version in the task-specific handoff. Use `check-source` for `implementation_unreleased`; use the ordered prepare/check-release-ready/commit/check-tag-ready/tag/verify-tag flow for `release_publication`. A source-state pass is not release or tag readiness.
> Operating model:
> - GPT owns architecture, behavior contracts, fixtures, tests, review, and the principal implementation.
> - The local agent owns integration, dependency restoration, compilation, runtime tests, and minimal integration corrections.
> - The local agent must not redesign approved behavior or weaken tests and acceptance criteria.
> - Do not hand-author `.gpt-workflow.lock`; use the pinned preparation prompt and official setup/update tooling.
> - GPT performs only static validation and does not execute runtime quality gates. GPT still authors the approved implementation, fixtures, and tests.
> - The local agent owns runtime integration and gates.
> - Release-commit CI must pass before tagging; final tag CI is external metadata.
> - Never force-push or use broad `git push --tags`.
> - Before release task authoring, load and validate the explicit project declaration with `python3 scripts/validate-release-publication.py release-publication.json --repo .`.
> - Before task authoring, read and validate the root `project-workflow.json` and `quality-gates.json` declarations. Do not execute declaration commands outside future deterministic tooling.
> - After `git push origin refs/tags/v<TARGET_VERSION>:refs/tags/v<TARGET_VERSION>`, derive the post-tag proof from that declaration: `none` has no publication task, `tag_only` verifies declared tag CI, and `github_actions` verifies the declared publication workflow plus GitHub Release/assets when expected.
> - Owner authorization to push the exact tag includes only declaration-authorized automatic workflow side effects; it does not authorize manual API/CLI publication, installation, activation, restart, or connector refresh.
> - Local `gh`, curl, wget, `GH_TOKEN`, and `GITHUB_TOKEN` publication is forbidden.
<!-- END GPT-REVIEW-PLANNER -->
