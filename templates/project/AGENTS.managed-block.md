<!-- BEGIN GPT-REVIEW-PLANNER -->
[Procedure index](../docs/PROCEDURE_INDEX.md) is the primary discovery entry point. After a terminal status, consult it and emit the next-transition handoff.
> [!IMPORTANT]
> Before substantial planning, implementation, review, or correction work,
> load the external workflow pinned by [`.gpt-workflow.lock`](./.gpt-workflow.lock).
>
> Canonical repository: [`https://github.com/rceman/gpt-review-planner`](https://github.com/rceman/gpt-review-planner)
>
> The installed block also contains a direct link to the exact commit-pinned
> `GPT_REVIEW_PLANNER.md`.
> Attached archive reviews default to the exact commit-pinned
> `prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md`; review-only mode uses
> `prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md` only when explicitly requested.
> Archive preparation uses `prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md`
> and `docs/PROJECT_ARCHIVE_REVIEW.md`; releases use `docs/RELEASE_PROCESS.md`.
>
> Operating model:
> - GPT owns architecture, behavior contracts, fixtures, tests, static/artifact review, and the principal implementation. GPT does not execute runtime quality gates.
> - The local agent owns integration, dependency restoration, formatting, compilation, linting, runtime tests, benchmarks, evidence, and minimal integration corrections.
> - Regardless of the owner's conversation language, all local-agent communication and execution reports must be written in English; preserve exact repository-controlled literals without translation.
> - Read the pinned `docs/AGENT_COMMUNICATION_LANGUAGE.md` contract and do not duplicate instructions bilingually.
> - The local agent must not redesign approved behavior or weaken tests and acceptance criteria.
> - Before any executable gateway task is dispatched, GPT commits its durable plan record to the relevant gateway-hub project branch.
> - A gateway-managed task is terminal only after strict `agent-result.json` is validated through the generated `complete-task` command; interactive session text is not completion.
> - The local agent must finalize success, revision blockers, and failures through the gateway and must not ask the owner to continue the task interactively.
> - GPT authors the principal patch and tests; the local agent applies them, executes runtime gates, produces evidence, and makes only narrow verified repairs.
> - GPT reviews agent-reported runtime evidence without rerunning tests.
>
> Engineering baseline: when `engineering-profile.json` is present, validate
> it with the exact pinned planner checkout and follow the selected profile and
> relevant documents. Owner instructions win; apply exceptions narrowly and
> report policy conflicts instead of silently selecting another stack.
> Prefer Rust/Axum for new backend components; use Go/Gin only when selected or
> approved. Production Node.js backends and direct frontend database access are
> forbidden. PostgreSQL schema authority remains Liquibase. Python rules apply
> to tools/tests; a valid legacy Python exception does not demand rewrite.
<!-- END GPT-REVIEW-PLANNER -->

- For executable patch packs, create a direct two-file JSON evidence commit after the implementation commit and validate it with the pinned `verify-agent-evidence.py`; never embed the evidence commit SHA inside its own evidence.
- Use the repository release script for version changes, release commits, and tags. Do not manually synchronize version-bearing files.
- Keep committed evidence limited to pre-evidence facts and implementation CI; report final evidence-head and PR-head CI externally after pushing evidence, without amending the evidence commit.

Attached code-project reviews default to the pinned `prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md`; use `prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md` only when review-only mode is explicitly requested. Archive preparation uses the pinned `prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md` and official setup/update tooling. Never hand-author `.gpt-workflow.lock`. Release/version/tag requests require the pinned `docs/RELEASE_PROCESS.md`.
GPT performs only static validation and does not execute runtime quality gates.
GPT still authors the approved implementation, fixtures, and tests.
The local agent owns runtime integration and gates.

## Release procedure

Any request to release, bump a version, or create a version tag requires reading
`docs/RELEASE_PROCESS.md` completely. Use only the repository release automation;
the owner selects the target version and synchronized version files must not be
edited manually. Release-commit CI must pass before tagging, and final tag CI is
external metadata. Do not publish a GitHub Release without explicit authorization.
Never force-push, rewrite published history, or use broad `git push --tags`.
CI policy: resolve `required`, `auto`, `optional`, or `disabled` explicitly. Repository visibility alone MUST NOT decide whether remote CI is required.
