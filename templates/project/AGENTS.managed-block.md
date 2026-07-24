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
- Keep committed evidence limited to pre-evidence facts and implementation CI; report final evidence-head and PR-head CI externally after pushing evidence, without amending the evidence commit.

## Release procedure

Any request to release, bump a version, or create a version tag requires reading
`docs/RELEASE_PROCESS.md` completely. Use only the repository release automation;
the owner selects the target version and synchronized version files must not be
edited manually. Release-commit CI must pass before tagging, and final tag CI is
external metadata. Do not publish a GitHub Release without explicit authorization.
Never force-push, rewrite published history, or use broad `git push --tags`.
