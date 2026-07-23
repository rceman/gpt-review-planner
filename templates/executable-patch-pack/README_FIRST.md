# Read First

## Patch identity

- Patch ID: `REPLACE_PATCH_ID`
- Target repository: `REPLACE_REPOSITORY`
- Target branch: `REPLACE_BRANCH`
- Base revision: `REPLACE_BASE_REVISION`
- Workflow pin: see `manifest.json`

## Required order

1. Read the target repository's `AGENTS.md`.
2. Read `.gpt-workflow.lock` and load the exact pinned workflow.
3. Read every document in this patch pack.
4. Verify repository identity and base hashes.
5. Apply deletions, patch, overlay, fixtures, and documentation.
6. Restore locked dependencies.
7. Run targeted gates, then full gates.
8. Correct only verified integration defects.
9. Keep the final changed-path set exactly equal to `manifest.json`.
10. Record every deviation in `DEVIATIONS.md`.
11. Run `scripts/verify-agent-result.sh`.
12. Produce the required final report and archive.

## Critical restrictions

- Do not redesign approved behavior.
- Do not weaken tests or acceptance criteria.
- Do not update dependencies unless required and documented.
- Do not claim skipped tests passed.
- Do not silently change files outside the manifest scope.
