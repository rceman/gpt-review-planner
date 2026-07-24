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
