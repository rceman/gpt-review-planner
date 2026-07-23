# Executable Patch Pack Format

An Executable Patch Pack is a repository-aware implementation handoff authored
primarily by GPT.

It must contain:

- normative behavior;
- exact file-level implementation;
- target-language tests;
- canonical fixtures;
- validation truth;
- local-agent execution instructions;
- acceptance gates;
- workflow and repository pins.

The local agent integrates and proves the patch. It does not reinterpret the feature.

## Test-execution policy

GPT authors the implementation, tests, fixtures, patch payload, manifest, and
static/artifact review. GPT may inspect archive integrity, manifest consistency,
patch/overlay/file-scope consistency, placeholders, text, ASTs, and other
non-runtime metadata. GPT must not install dependencies, compile or build the
project, run formatters or project linters, execute tests, benchmarks, or smoke
checks, or start project services. Runtime validation is not executed by GPT.

The local coding agent restores dependencies, runs all required formatting,
compile, lint, unit, integration, E2E, benchmark, and runtime gates, fixes only
verified narrow integration defects, and records exact evidence. GPT reviews
that evidence without rerunning the gates.

Every `VALIDATION_REPORT.md` must have these separate sections:

```text
GPT_STATIC_CHECKS_PERFORMED
GPT_RUNTIME_CHECKS_NOT_PERFORMED
AGENT_RUNTIME_GATES_REQUIRED
AGENT_RUNTIME_RESULTS
```

Before agent execution, `AGENT_RUNTIME_RESULTS` must say exactly:
`Pending local-agent execution.`. The final agent result must distinguish
`Written by GPT`, `Executed by agent`, `Result`, and `Evidence or log location`.

## Exact file-scope invariant

The following sets must agree:

- `manifest.json` created, modified, and deleted paths;
- created and modified paths represented by `patch/changes.patch`;
- created and modified paths supplied by `overlay/`;
- `patch/delete-paths.txt`;
- the final repository diff from `target.base_revision`.

`changes.patch` paths are extracted through `git apply --numstat -z`, not by
manually splitting quoted `diff --git` headers. UTF-8 names, spaces, and embedded
whitespace therefore retain their exact repository spelling.

The final verifier preserves operation classes:

- `A` and untracked paths → created;
- `M` and `T` → modified;
- `D` → deleted;
- `R` → old path deleted and new path created;
- `C` → new path created.

Matching only the union of paths is insufficient. A manifest that declares a file
as modified must fail when the repository actually deletes it.

Every pack includes `DEVIATIONS.md` and `scripts/patch_pack_scope.py`. An undeclared
path or mismatched operation type is a blocking deviation, not an implicit
integration correction.
