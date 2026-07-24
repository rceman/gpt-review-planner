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
   `VALIDATION_REPORT.md`, `manifest.json`, `evidence.json`, and `expected/*`.
5. Verify the target repository and base revision.
6. Apply the supplied implementation rather than reimplementing it from prose.
7. Restore dependencies and execute all required gates. Runtime validation is
   owned by the local coding agent; GPT does not rerun these gates.
8. Fix only verified compilation or integration defects.
9. Add regression coverage for each correction.
10. Keep the final repository diff exactly equal to the manifest file scope.
11. Record every deviation structurally in `evidence.json`; use an empty
    `deviations` array when there are none.
12. Run `scripts/verify-agent-result.sh` before reporting completion.
13. Produce `AGENT_RESULT.md` with commands, results, warnings, deviations,
   unresolved risks, final commit, and archive SHA-256 when required.

The authored `VALIDATION_REPORT.md` must separate:

```text
GPT_STATIC_CHECKS_PERFORMED
GPT_RUNTIME_CHECKS_NOT_PERFORMED
AGENT_RUNTIME_GATES_REQUIRED
AGENT_RUNTIME_RESULTS
```

Before execution, `AGENT_RUNTIME_RESULTS` must say
`Pending local-agent execution.`. In the final report distinguish `Written by
GPT`, `Executed by agent`, `Result`, and `Evidence or log location`.

Do not add, remove, or modify repository paths outside the manifest scope. Stop and
report the required deviation instead. Do not change formulas, state transitions,
timing, validation, public semantics, security boundaries, compatibility, or
acceptance criteria without explicit approval.

## Evidence commit procedure

1. Commit the validated implementation and record its full SHA.
2. Create the exact directory from `manifest.evidence_directory`.
3. Copy this pack's `manifest.json` byte-for-byte into that directory.
4. Complete `evidence.json`: set `implementation_commit`; include every manifest requirement with status and verifiable proofs; include every manifest gate with compact results; add structured deviations only when needed.
5. Run `bash scripts/verify-agent-result.sh prepare <repo> <implementation-sha>`.
6. Commit exactly the two evidence files.
7. Run `bash scripts/verify-agent-result.sh committed <repo> <implementation-sha> HEAD`.
