<!-- BEGIN GPT-REVIEW-PLANNER -->
> [!IMPORTANT]
> Before substantial planning, implementation, review, or correction work,
> load the external workflow pinned by [`.gpt-workflow.lock`](./.gpt-workflow.lock).
>
> Canonical repository: [`https://github.com/rceman/gpt-review-planner`](https://github.com/rceman/gpt-review-planner)
>
> The installed block also contains a direct link to the exact commit-pinned
> `GPT_REVIEW_PLANNER.md`.
>
> Operating model:
> - GPT owns architecture, behavior contracts, fixtures, tests, static/artifact review, and the principal implementation. GPT does not execute runtime quality gates.
> - The local agent owns integration, dependency restoration, formatting, compilation, linting, runtime tests, benchmarks, evidence, and minimal integration corrections.
> - The local agent must not redesign approved behavior or weaken tests and acceptance criteria.
> - GPT reviews agent-reported runtime evidence without rerunning tests.
<!-- END GPT-REVIEW-PLANNER -->

- For executable patch packs, create a direct two-file JSON evidence commit after the implementation commit and validate it with the pinned `verify-agent-evidence.py`; never embed the evidence commit SHA inside its own evidence.
- Use the repository release script for version changes, release commits, and tags. Do not manually synchronize version-bearing files.
