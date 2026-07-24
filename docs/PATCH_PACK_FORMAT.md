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
whitespace therefore retain their exact repository spelling. Leading and trailing
spaces are significant and must not be trimmed by the manifest, overlay, patch, or
deletion-list validators.

Native Git rename/copy numstat records are supported. In NUL-delimited numstat,
these records expose an empty pathname field followed by separate old and new
pathnames; both paths are included in patch payload scope. The final-result verifier
continues to classify rename as old deleted plus new created, and copy as new
created.

NUL, LF, and CR characters in repository paths are not supported by the patch-pack
manifest and line-based deletion-list format and must be rejected explicitly.

The final verifier preserves operation classes:

- `A` and untracked paths → created;
- `M` and `T` → modified;
- `D` → deleted;
- `R` → old path deleted and new path created;
- `C` → new path created.

Matching only the union of paths is insufficient. A manifest that declares a file
as modified must fail when the repository actually deletes it.

Every canonical pack includes `manifest.json`, a pending `evidence.json` template,
and `scripts/patch_pack_scope.py`. Deviations are structured JSON entries in the
completed evidence file. An undeclared path or mismatched operation type is a
blocking deviation, not an implicit integration correction.

## Timestamp identity, requirements, and JSON evidence

Schema version 2 adds `title`, `description`, `created_at`, `patch_timestamp`, `patch_slug`, `baseline_release`, `evidence_directory`, stable `requirements`, and required `gates`.

The canonical patch ID is:

```text
patch-<UTC-YYYYMMDD-HHMMSS>-<one-to-three-word-slug>
```

After runtime validation, the agent commits exactly two evidence files:

```text
manifest.json
 evidence.json
```

The saved manifest is byte-identical to the pack manifest. `evidence.json` does not repeat manifest commands, requirement text, acceptance criteria, expected scope, patch identity, or evidence commit SHA. It records compact requirement proof references, compact gate results, and deviations.

Every manifest requirement must appear exactly once in evidence. Passing requirements require verifiable proof from the implementation commit. Every manifest gate must appear exactly once and pass. The pinned evidence checker verifies these claims and Git history without executing the project gates again.

## Pre-evidence gates and external final-head CI

Committed gates are limited to facts knowable before the evidence commit is
created: local commands, implementation scope, evidence preparation, and
implementation-commit CI. A gate whose `head` is `evidence` or whose result
depends on the evidence commit itself is invalid. Final evidence-head or later
PR-head CI is run after the evidence commit and reported only as external
GitHub/PR metadata. The agent must not amend the evidence commit to insert a
self-referential CI run or commit SHA.
