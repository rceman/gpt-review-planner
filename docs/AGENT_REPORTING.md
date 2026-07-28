# Agent Reporting Contract

This contract is the human/GPT projection of machine-verifiable execution evidence.

1. Report each fact once.
2. Omit raw command output when a concise result is sufficient.
3. Do not repeat values already in a canonical record.
4. Preserve exact error output for failures and diagnostics.
5. Group test counts by gate.
6. Keep full logs in the execution environment unless needed to explain failure.
7. Committed evidence remains authoritative and is not replaced by a summary.

For successful CI, emit exactly one compact record:

```text
Merge CI: success | sha=<SHA> | run=<RUN_ID> | job=<JOB_ID_OR_NULL> | run_url=<RUN_URL> | job_url=<JOB_URL_OR_NULL>
```

Use `Implementation CI`, `Evidence CI`, `Merge CI`, `Release CI`, or `Tag CI` as appropriate. Do not repeat state, blocking, policy, repository, IDs, URLs, checked SHA, status, or conclusion after the record. Successful helper JSON is not pasted before repeated fields.

For failure, use one record such as:

```text
Merge CI: failed | blocking=true | sha=<SHA> | run=<RUN_OR_NULL> | job=<JOB_OR_NULL> | exit=<EXIT_CODE> | message=<DETERMINISTIC_MESSAGE>
```

Raw JSON is included once only for blocking, invalid, internally inconsistent, diagnostically important unavailable results, or explicit owner request. Permitted absence is reported as `Implementation CI: no_run | blocking=false | policy=auto | sha=<SHA> | message=<SUMMARY>` and is never called success.

Final reports normally contain terminal status, identity, changed scope, grouped gates, one CI record per observed SHA, evidence identity, final Git/ref/worktree state, and prohibited-operation confirmation. Machine evidence must retain all required fields in manifests, evidence, schemas, and helper output.
