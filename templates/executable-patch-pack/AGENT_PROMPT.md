# Local Agent Mission

Apply and integrate this GPT-authored Executable Patch Pack.

## Inputs

- Target repository: `REPLACE_REPOSITORY_PATH`
- Patch pack: this directory
- Required branch: `REPLACE_BRANCH`

## Instructions

1. Read `<repository>/AGENTS.md`.
2. Read `<repository>/.gpt-workflow.lock`.
3. Load the exact workflow revision pinned by that lock.
4. Read `README_FIRST.md`, `PATCH_SPEC.md`, `BEHAVIOR_CONTRACT.md`,
   `VALIDATION_REPORT.md`, `manifest.json`, and `expected/*`.
5. Verify the target repository and base revision.
6. Apply the supplied implementation rather than reimplementing it from prose.
7. Restore dependencies and execute all required gates.
8. Fix only verified compilation or integration defects.
9. Add regression coverage for each correction.
10. Record material deviations using the deviation schema.
11. Produce `AGENT_RESULT.md` with commands, results, warnings, deviations,
    unresolved risks, final commit, and archive SHA-256 when required.

Do not change formulas, state transitions, timing, validation, public semantics,
security boundaries, compatibility, or acceptance criteria without explicit approval.
