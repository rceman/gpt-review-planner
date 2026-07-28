# GPT Review Planner

**Workflow version:** 1.0.0  
**Status:** Active  
**Canonical repository:** `https://github.com/rceman/gpt-review-planner`  
**Default document:** `GPT_REVIEW_PLANNER.md`  
**Applies to:** planning, implementation, review, correction patches, refactoring, migrations, verification, and agent handoff.

---

## 1. Purpose

This workflow combines two models with deliberately different responsibilities:

- **GPT** is the principal architect, behavior owner, reviewer, test designer, and code author.
- **The local coding agent** is the repository operator, integration engineer, compiler operator, test runner, and implementation finisher.
- **The project owner** controls product intent, scope, and final approval.

The [engineering baseline](docs/engineering/README.md) is the normative load
map for stack, language, framework, database, profile, exception, and review
policy. Its registry and target declarations are checked by dependency-free
engineering validators.

The objective is to minimize both:

1. time spent by GPT installing dependencies, compiling full workspaces, launching browsers, databases, containers, or long-running test suites;
2. tokens spent by the local agent rediscovering architecture, inventing behavior, writing routine code, or interpreting vague prose.

The expected operating model is:

```text
GPT provides intelligence and most of the implementation.
The local agent provides environment execution and evidence.
```

## Attached project archive workflow

For attached code projects, use the [canonical archive-review guide](docs/PROJECT_ARCHIVE_REVIEW.md),
the [review-and-implement prompt](prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md),
the [review-only prompt](prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md), and the
[local archive-preparation prompt](prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md).
Prepared archives are preferred for recurring projects and must use official
tooling to generate `.gpt-workflow.lock`; raw archives may use an immutable prompt
URL without a lock. Preferred archive preparation is a compact immutable link
plus optional owner objective:

```text
Prepare review archive using:
https://github.com/rceman/gpt-review-planner/blob/vX.Y.Z/prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md

We want to remove all AnyDesk occurrences because we are switching to RustDesk only.
```

This requests a full review with the migration as a mandatory priority overlay;
it is not objective-only. Explicitly say `Limit the review strictly to the
AnyDesk-to-RustDesk migration.` to restrict scope. Preparer observations and
questions travel in the manifest as untrusted context and require independent
verification. In staging, the immutable methodology URL is the explicit staged
workflow selection: matching source locks are preserved, older valid locks are
reconciled only in the temporary staging copy with official tooling, and source
lock/`AGENTS.md` files remain unchanged. Integrate-source requires separate
authorization to modify source. Expanded invocations remain supported for automation. Immutable
tag or commit links are required; do not use `main`.
The universal preparation flow also generates `.gpt-review/archive-manifest.json`
for provenance and task context. Downstream workflow metadata never changes the
complete archive inclusion contract.
Archive preparation always passes the owner-selected immutable `--version REF`;
an optional exact `--commit SHA` must match it and never replaces the required
version argument.

The local agent must receive enough exact code, fixtures, tests, file paths, and acceptance criteria that its task becomes a constrained integration and verification problem rather than a new implementation project.

---

## 2. Authority and precedence

For any task, apply sources in this order:

1. current explicit instructions from the project owner;
2. approved task-specific specifications and ADRs;
3. the task-specific behavior contract;
4. the task-specific patch specification;
5. repository-specific `AGENTS.md`;
6. the pinned revision of this workflow;
7. existing repository conventions and historical behavior.

Conflicts between higher-priority sources must be reported. They must not be silently resolved by weakening requirements.

### 2.1 Bounded review and closure

Load [`docs/REVIEW_CLOSURE_PROTOCOL.md`](docs/REVIEW_CLOSURE_PROTOCOL.md) and
`profiles/review-closure.json` for review-to-implementation tasks. Validate the
machine contract with `scripts/validate-review-closure.py`.

The first review is full within the effective owner-selected scope. The exact
proposed patch scope MUST contain stable acceptance-criterion IDs, covered
finding IDs, file operations, exclusions, and required gates. Explicit owner
approval creates the scope lock.

After implementation or a correction, the normal review mode is `delta`: verify
approved findings, changed surfaces, acceptance criteria, required evidence, and
demonstrable regressions. Do not restart an unconstrained full review. A full
reopen requires an explicit owner request, a material architecture change, or
new concrete evidence of a critical/high-severity defect.

A new finding blocks merge only when it has an evidenced blocking basis: failed
approved acceptance criterion, demonstrable regression, critical/high defect,
security vulnerability, data loss/corruption, broken public contract, failed
required gate, or materially unusable approved behavior. Hardening,
completeness, maintainability, optional test expansion, future architecture,
style, and a newly proposed stronger contract are follow-up work unless the
owner explicitly promotes them into scope.

Implementation-result reviews separate `MERGE_BLOCKERS`, `FOLLOW_UP_BACKLOG`,
and `OBSERVATIONS`. One normal correction round is allowed. When approved
criteria and gates pass, declared and actual scope agree, and no evidenced
blocker remains, declare `MERGE_READY` and stop the current review. Do not keep
searching for optional improvements after closure.

`MERGE_READY` authorizes a merge but does not finalize Git integration. A merge
task becomes `MERGE_FINALIZED` only after exact merge-SHA CI succeeds, the
reviewed remote feature tip is verified as an ancestor, the remote feature
branch is deleted through the configured SSH `origin`, refs are pruned, and
the local feature branch is retained. If safe deletion fails after successful
merge CI, report `MERGE_CLEANUP_BLOCKED`. Follow the normative
[`POST_MERGE_BRANCH_CLEANUP.md`](docs/POST_MERGE_BRANCH_CLEANUP.md); `gh`,
GitHub APIs, fallback HTTPS remotes, squash, and history rewriting are forbidden.
Its machine-critical identity and ancestry checks use fully qualified refs to
prevent local-branch shadowing.

All local-agent-facing communication MUST be written in English, regardless of
the language used by the owner when communicating with GPT. This includes every
`AGENT_HANDOFF`, `AGENT_PROMPT.md`, implementation, correction, merge, cleanup,
and release instruction, plus every agent question, progress report, blocker,
deviation, and final execution report. Exact repository-controlled literals may
remain in their original language. Follow
[`AGENT_COMMUNICATION_LANGUAGE.md`](docs/AGENT_COMMUNICATION_LANGUAGE.md);
bilingual agent instructions are forbidden.

---

## 3. Responsibility model

### 3.1 GPT owns

GPT is responsible for:

- understanding the requested feature, defect, refactor, or review;
- inspecting the actual repository and relevant documentation;
- identifying affected modules, contracts, schemas, and tests;
- deciding the architecture unless the project owner reserves that decision;
- defining behavior, edge cases, invariants, and failure semantics;
- preparing canonical fixtures;
- writing native tests in the target language;
- writing the principal production implementation;
- writing migration, compatibility, and rollout logic;
- preparing machine-applicable patches or complete overlay files;
- performing GPT static review and non-runtime artifact validation only;
- documenting what was and was not executed;
- reviewing the local agent's integrated result;
- producing correction patches when the result is incomplete.

GPT must not leave ordinary implementation work to the local agent merely because the agent is capable of doing it.

### 3.2 Local agent owns

The local agent is responsible for:

- verifying repository identity, branch, and base revision;
- loading the pinned workflow;
- applying the supplied patch or overlay;
- restoring locked dependencies;
- running formatters, compilers, type checkers, tests, browsers, containers, databases, and services;
- resolving actual compile and integration defects;
- adding regression coverage for integration defects;
- preserving the supplied behavior contract;
- documenting every material deviation;
- producing exact command, test, and artifact evidence.

The local agent is not the default architecture owner.

### 3.3 Project owner owns

The project owner controls:

- product intent;
- requested scope;
- feature priorities;
- material architecture changes;
- material dependency additions;
- acceptance of behavioral changes;
- final approval.

### 3.4 Normative test-execution policy

The validation roles are strictly separated.

#### GPT / ChatGPT architect-reviewer

GPT may:

- analyze the repository statically;
- write specifications, fixtures, production code, and tests;
- prepare patches, overlays, manifests, expected file scopes, and review reports;
- perform non-runtime artifact checks such as archive integrity, manifest
  consistency, patch/overlay/file-scope consistency, unresolved-placeholder
  detection, textual inspection, AST-level inspection, and syntax-only checks
  that do not compile or execute project code.

GPT must not:

- install or update project dependencies;
- run unit, integration, end-to-end, benchmark, or property tests;
- compile or build the project;
- run formatters or linters that execute project tooling;
- start project services, databases, browsers, containers, or application
  binaries;
- claim runtime validation based on its own sandbox execution.

GPT writes tests but leaves every executable quality gate to the local coding
agent. A test written by GPT is neither executed nor passing until the local
coding agent runs it and records the result.

#### Local coding agent

The local coding agent applies the GPT-authored patch, restores or installs
dependencies, runs formatting, compilation, linting, unit, integration, E2E,
benchmark, and other runtime gates, fixes only verified narrow integration
defects, adds regression coverage for each correction, and records exact
commands, outputs, failures, fixes, and final results.

GPT then reviews the final diff, declared versus actual file scope,
agent-reported test evidence, deviations, and acceptance-gate results. GPT does
not rerun tests during this review.

Use these exact report terms:

- `GPT static review`;
- `GPT artifact validation`;
- `agent runtime validation`;
- `agent-executed quality gates`;
- `runtime validation not executed by GPT`.

Every patch-pack report also has these mandatory sections:

```text
GPT_STATIC_CHECKS_PERFORMED
GPT_RUNTIME_CHECKS_NOT_PERFORMED
AGENT_RUNTIME_GATES_REQUIRED
AGENT_RUNTIME_RESULTS
```

Before agent execution, `AGENT_RUNTIME_RESULTS` says
`Pending local-agent execution.`.

Avoid ambiguous claims such as “GPT validates the tests,” “GPT runs
validation,” “locally validated by GPT,” or “GPT executes smoke tests.”

---

## 4. Non-negotiable principles

### 4.1 Actual code over pseudocode

Pseudocode may explain an algorithm, but it must not replace production code when repository sources are available.

Unacceptable handoff content includes:

```text
TODO: implement validation
Call the existing service here
Handle errors as appropriate
Add tests for edge cases
```

The preferred output is:

- complete new files;
- exact diffs for existing files;
- real tests;
- real fixtures;
- real schemas;
- executable validation scripts;
- exact residual integration work.

### 4.2 Behavior before infrastructure

Use this order by default:

```text
Behavior contract
→ canonical fixtures
→ native tests
→ pure/domain implementation
→ infrastructure adapters
→ full integration
```

### 4.3 Tests define completion

Important requirements must be represented by tests, fixtures, golden files, state-transition tables, property checks, or deterministic scenarios.

A feature is not complete when tests are absent, ignored, weakened, or replaced by prose.

### 4.4 Isolate pure logic

Where practical, domain logic must be separated from:

- HTTP and WebSocket transport;
- databases and filesystems;
- browser and UI frameworks;
- process supervision;
- environment configuration;
- dependency-heavy adapters.

This makes important behavior independently compilable or executable.

### 4.5 No unnecessary dependencies

Prefer, in order:

1. standard library;
2. an existing project dependency;
3. an existing project utility;
4. a small local module;
5. a new external dependency only with explicit justification.

Every new dependency must document purpose, alternatives, enabled features, compile-time cost, runtime cost, maintenance cost, and security implications.

### 4.6 Integration fixes are not redesign permission

The local agent may correct imports, visibility, types, ownership, lifetimes, trait bounds, framework API drift, serialization wiring, fixture paths, and test harness integration.

It must not silently change formulas, timings, state transitions, validation rules, error semantics, compatibility, security boundaries, or acceptance criteria.

---

## 5. Supported task modes

### 5.1 New feature

GPT defines the contract, tests, fixtures, implementation, and executable patch. The local agent integrates and verifies it.

### 5.2 Existing implementation review

GPT compares an archive, branch, commit, or diff against approved requirements, identifies defects, and produces an executable correction patch with exact code and tests.

### 5.3 Defect repair

GPT specifies a reproducing test or fixture, identifies the root cause from
static evidence, writes the fix, and delegates test execution and environment
validation to the local coding agent.

### 5.4 Refactor

GPT first defines characterization tests and expected behavior, then prepares the
structural change. The local agent executes the tests and proves behavioral
equivalence.

### 5.5 Architecture planning

When code is premature, GPT produces ADRs, contracts, schemas, fixtures, migration rules, and implementation-ready task decomposition.

### 5.6 Final verification

GPT reviews the final diff, test evidence, dependency changes, skipped gates, warnings, and deviations, then classifies the result as approved, approved with follow-up, correction required, or rejected.

---

## 6. Standard GPT workflow

### Phase 0 — Normalize input

Identify:

- target repository;
- branch or base revision;
- requested output;
- authoritative specifications;
- scope boundaries;
- compatibility requirements;
- task mode.

### Phase 1 — Repository reconnaissance

Without installing dependencies unless necessary, inspect:

- repository tree;
- manifests and lock files;
- workspace/package structure;
- module exports and entry points;
- domain types and traits;
- related implementations;
- test conventions and fixtures;
- schemas and migrations;
- generated-code boundaries;
- CI and build configuration;
- ADRs and project documentation.

Produce an affected-file map and integration-risk list.

Useful lightweight commands include:

```bash
git ls-files
git grep
rg
find
sed
awk
git diff
git log
cargo metadata --offline --no-deps
```

### Phase 2 — Behavior contract

Define as applicable:

- inputs and outputs;
- valid and invalid states;
- state transitions;
- invariants;
- ordering and timing;
- validation;
- retry and idempotency;
- concurrency;
- errors;
- serialization;
- security boundaries;
- compatibility;
- observability;
- performance constraints;
- determinism;
- prohibited behavior.

Use state-transition tables for temporal behavior.

### Phase 3 — Canonical fixtures

Create deterministic fixtures for:

- valid cases;
- invalid cases;
- boundaries;
- regressions;
- serialized messages;
- state snapshots;
- event sequences;
- expected outputs.

Randomized cases must include fixed seeds.

### Phase 4 — Native target-language tests

Write the actual tests, not test instructions.

Cover:

- happy path;
- invalid input;
- boundaries;
- error propagation;
- state transitions;
- duplicate operations;
- retry behavior;
- compatibility;
- deterministic output;
- regressions;
- prohibited behavior.

### Phase 5 — Principal production implementation

Write:

- data structures;
- algorithms;
- state machines;
- validation;
- errors;
- adapters;
- exports;
- configuration;
- migrations;
- documentation;
- test helpers;
- removal of replaced code.

Avoid placeholders such as `TODO`, `unimplemented!()`, fake production mocks, or constant success returns.

### Phase 6 — GPT static and artifact validation

GPT may perform only checks that inspect text, metadata, or archive structure
without compiling or executing project code. Examples include:

```bash
# Artifact and repository metadata
git diff --check
find . -name '*Zone.Identifier*' -o -name '*Zone.Identifier'
```

GPT may also scan for placeholders, broken fixture paths, accidental dependency
changes, secrets, machine-specific paths, and out-of-scope files. These checks
are static or artifact checks, not tests or runtime validation.

Dependency restoration, compiler bootstrap, syntax checks that execute a
compiler, formatting, linting, compilation, tests, benchmarks, and smoke checks
belong to the local coding agent. GPT records them under
`GPT_RUNTIME_CHECKS_NOT_PERFORMED` and `AGENT_RUNTIME_GATES_REQUIRED`.

### Phase 7 — Package the Executable Patch Pack

The handoff must be self-contained and machine-applicable wherever possible.

---

## 7. Optional reference oracle

A standard-library-only Python reference is recommended when it materially improves confidence in:

- formulas;
- state machines;
- economy and combat simulations;
- cooldown timelines;
- targeting priorities;
- deterministic random sequences;
- scoring;
- timeout resolution;
- fixture generation;
- property-style checks.

The Python model is an oracle, not the production authority. Target-language code and task-specific contracts remain authoritative.

Do not build Python mirrors for framework-specific behavior such as Axum routing, Tokio cancellation, database transactions, Svelte lifecycle, browser rendering, or TypeScript type inference.

---

## 8. Standalone native kernels

Important domain modules should be independently testable when this fits the architecture naturally.

For Rust, prefer:

- standard-library-only types;
- pure functions;
- deterministic transitions;
- no async runtime in the domain kernel;
- no transport or persistence inside the kernel.

Example agent runtime gate:

```bash
rustc --edition=2021 --test damage_kernel.rs -o /tmp/damage-kernel-tests
/tmp/damage-kernel-tests
```

The local coding agent executes this gate and reports its output. GPT may review
the code and the agent's evidence, but does not run the compiler or tests.

---

## 9. Executable Patch Pack format

Recommended structure:

```text
<patch-id>/
├── AGENT_PROMPT.md
├── README_FIRST.md
├── PATCH_SPEC.md
├── BEHAVIOR_CONTRACT.md
├── VALIDATION_REPORT.md
├── evidence.json
├── manifest.json
├── patch/
│   ├── changes.patch
│   ├── delete-paths.txt
│   └── base-file-hashes.sha256
├── overlay/
├── fixtures/
├── reference/
├── scripts/
│   ├── apply.sh
│   ├── validate-static.sh
│   ├── run-reference-tests.sh
│   ├── patch_pack_scope.py
│   └── verify-agent-result.sh
└── expected/
    ├── file-tree.txt
    ├── test-list.txt
    ├── acceptance-gates.md
    └── allowed-deviations.md
```

Omit directories that are genuinely unused.

### Required document roles

- `README_FIRST.md`: repository, branch, base revision, order, warnings, deliverables.
- `AGENT_PROMPT.md`: one self-contained local-agent mission.
- `PATCH_SPEC.md`: architecture, exact file changes, schemas, migrations, tests, acceptance.
- `BEHAVIOR_CONTRACT.md`: normative behavior.
- `VALIDATION_REPORT.md`: separate GPT static checks, GPT runtime checks not
  performed, required agent gates, and agent runtime results.
- `manifest.json`: machine-readable scope, risks, required gates, and workflow pin.
- `evidence.json`: compact implementation-commit proofs, gate results, and structured deviations.
- `patch_pack_scope.py`: validates pack payload scope and the final repository diff.

The created, modified, and deleted paths in `manifest.json` are authoritative. When
present, `changes.patch` and `overlay/` must match the manifest create/modify set,
while `delete-paths.txt` must match the manifest delete set exactly. Patch paths must
be parsed by Git in NUL-delimited mode so UTF-8 names and whitespace remain exact.

Before completion, the final repository diff from the pinned base revision must
match both the complete path set and each operation class. Treat `A` and untracked
paths as created, `M`/`T` as modified, `D` as deleted, `R` as old deleted plus new
created, and `C` as new created. An additional path or a created/modified/deleted
classification mismatch is a blocking deviation and requires an updated patch pack
or explicit owner approval.

---

## 10. Confidence classification

### GREEN — GPT static review complete

Examples:

- archive and manifest structure checked;
- fixtures and patch payloads inspected;
- generated patch scope checked;
- textual or AST-level inspection completed.

GREEN does not imply compilation, runtime validation, or passing tests.

### YELLOW — agent runtime validation required

Examples:

- crate adapter;
- async wiring;
- route;
- migration;
- browser component;
- serialization adapter;
- workspace integration test.

YELLOW code must still be complete, not a placeholder. The local coding agent
must execute and report the required quality gates.

### RED — unresolved or blocked

Examples:

- missing source;
- unknown generated contract;
- unavailable production data;
- material repository conflict.

RED items must be explicit. An implementation-ready handoff must not hide them.

---

## 11. Local-agent execution contract

The local agent must:

1. verify repository path, branch, base revision, and working tree;
2. load `AGENTS.md`, `.gpt-workflow.lock`, and the pinned workflow;
3. read every patch-pack document;
4. verify base hashes;
5. create or switch to the required branch;
6. apply deletions, patch, overlay, fixtures, and docs;
7. restore only locked or approved dependencies;
8. run fast gates before expensive gates;
9. correct only verified compile and integration defects;
10. add regression coverage for each correction;
11. run every required acceptance gate;
12. produce a final evidence report.

Recommended gate order:

```text
formatting
→ syntax
→ type checking
→ targeted unit tests
→ targeted integration tests
→ package tests
→ workspace tests
→ build
→ E2E
→ extended validation
```

A skipped gate is not a passed gate.

---

## 12. Permitted local-agent corrections

Permitted without separate approval when behavior is preserved:

- imports and module registration;
- visibility;
- formatting;
- type conversions;
- trait bounds;
- ownership and lifetimes;
- non-semantic API version drift;
- fixture path resolution;
- test setup;
- repository-specific error wrapping;
- warnings introduced by the patch.

Requires explicit approval:

- removing acceptance criteria;
- deleting or weakening failing tests;
- marking required tests ignored;
- changing formulas, timings, or state transitions;
- altering public API semantics;
- adding major dependencies;
- replacing architecture components;
- disabling security checks;
- bypassing authorization;
- changing protocol or persistence semantics;
- substantially widening scope.

---

## 13. Deviation protocol

Every completed evidence record contains a `deviations` array. Use an empty array
when the agent made no deviation. Add a structured entry when a deviation is
required:

```text
{
  "id": "D1",
  "kind": "integration",
  "summary": "...",
  "scope_changed": false,
  "behavior_changed": false,
  "requirements": ["R2"]
}
```

A successful build is not sufficient justification for a behavioral deviation.
A change outside the manifest file scope must not be merged merely because it is
mechanical or makes tests pass; it requires an updated patch pack or explicit owner
approval.

---

## 14. GPT review of agent output

Review:

### Scope

- required files present;
- no unrelated subsystem changes;
- no missing cleanup;
- generated artifacts intentional.

### Behavior

- contract and fixtures satisfied;
- transitions complete;
- validation correct;
- ordering and timing correct;
- compatibility preserved;
- failures explicit.

### Code quality

- boundaries respected;
- duplication and coupling acceptable;
- errors propagated;
- panic paths justified;
- concurrency safe;
- dependencies justified.

### Test quality

- agent evidence shows real behavior executed;
- assertions are meaningful;
- negative and regression cases present;
- deterministic;
- not over-mocked;
- capable of failing when implementation is broken.

GPT reviews the agent's evidence and does not rerun these tests.

### Deviations

Each deviation must be accepted, corrected, or rejected.

---

## 15. Quality gates and Definition of Done

A task is complete only when applicable gates pass under the local coding
agent's execution. GPT may review the evidence but does not execute these gates:

- repository cleanliness;
- formatting;
- syntax;
- linting;
- type checking;
- unit tests;
- integration tests;
- fixture validation;
- serialization tests;
- migration tests;
- deterministic replay tests;
- workspace build;
- production build;
- browser smoke tests;
- E2E;
- security checks;
- dependency audit;
- archive hygiene;
- SHA-256;
- final GPT review.

Completion requires:

1. behavior contract satisfied;
2. production code present;
3. tests and fixtures present;
4. no placeholders;
5. required gates executed;
6. failures and skips documented;
7. deviations reviewed;
8. docs and ADRs updated;
9. final result reviewed by GPT using agent evidence without rerunning tests;
10. final artifact reproducible where requested.

Compilation alone is not completion.

---

## 16. Archive hygiene

Remove before packaging:

```text
*:Zone.Identifier
*Zone.Identifier
.DS_Store
Thumbs.db
__MACOSX
__pycache__
.pytest_cache
node_modules
target
dist
build
coverage
temporary logs
editor caches
runtime secrets
```

For final archives:

1. create archive;
2. list contents;
3. verify exclusions;
4. extract into a clean temporary directory;
5. verify expected files;
6. calculate SHA-256;
7. report size and hash.

---

## 17. Token and time optimization

### GPT should minimize

- dependency installation;
- full builds before source completion;
- repeated scans;
- prose where exact code is possible;
- duplicate specifications;
- Python mirrors of framework behavior;
- unsupported claims about tests.

### GPT should maximize

- exact file maps;
- fixtures;
- standalone tests;
- complete code;
- deterministic examples;
- machine-applicable patches;
- explicit residual integration work.

### Local agent should minimize

- rediscovery;
- redesign;
- restating requirements;
- implementing code already supplied;
- full suites before targeted tests;
- unnecessary sub-agents;
- long narrative logs.

### Local agent should maximize

- applying;
- compiling;
- testing;
- correcting;
- verifying;
- evidence.

---

## 18. External repository integration: Option A

Projects do not copy this full document. They contain:

```text
AGENTS.md
.gpt-workflow.lock
```

`AGENTS.md` contains a managed workflow block. `.gpt-workflow.lock` pins:

- canonical repository URL;
- release tag or version;
- exact commit SHA;
- document path.

The exact commit is authoritative. A moving branch such as `main` must not be used as the reproducibility pin.

Install into a project with the canonical repository's `setup.sh`. Update the pin with `update.sh`.

---

## 19. Required managed block in AGENTS.md

The setup script inserts a block equivalent to:

```md
<!-- BEGIN GPT-REVIEW-PLANNER -->
> [!IMPORTANT]
> Before substantial planning, implementation, review, or correction work,
> load the external workflow pinned by [`.gpt-workflow.lock`](./.gpt-workflow.lock).
>
> Canonical repository: `https://github.com/rceman/gpt-review-planner`
>
> Operating model:
> - GPT owns architecture, behavior contracts, fixtures, tests, review, and the principal implementation.
> - The local agent owns integration, dependency restoration, compilation, runtime tests, and minimal integration corrections.
> - The local agent must not redesign approved behavior or weaken tests and acceptance criteria.
<!-- END GPT-REVIEW-PLANNER -->
```

The block is managed. Re-running setup or update replaces it idempotently.

---

## 20. ChatGPT Project integration

For each ChatGPT Project:

1. upload the pinned `GPT_REVIEW_PLANNER.md`;
2. upload relevant repository `AGENTS.md`;
3. keep the workflow version and commit visible;
4. replace stale project-source copies when the project pin changes;
5. record the workflow pin in every patch manifest.

The repository copy and Git tag history are canonical. ChatGPT Project sources are cached working copies.

---

## 21. Versioning

Use semantic versioning and Git tags:

- PATCH: wording or clarification without process changes;
- MINOR: backward-compatible workflow additions;
- MAJOR: changed responsibilities, artifact contracts, or mandatory order.

The active filename remains stable:

```text
GPT_REVIEW_PLANNER.md
```

Do not create `final`, `rev2`, or versioned active filenames. Git history and tags preserve old revisions.

---

## 22. Standard GPT mission

```text
Use the workflow pinned by .gpt-workflow.lock.

Inspect the supplied repository or archive and prepare an Executable Patch Pack.
Own the architecture, behavior contract, fixtures, native tests, review, and
principal production implementation.

Do not install dependencies, compile, or execute project tests, benchmarks, or
runtime smoke checks. Perform only GPT static review and non-runtime artifact
validation, and report runtime validation as not executed by GPT.

Leave the local agent dependency restoration, formatting, compilation, linting,
runtime test execution, benchmarks, evidence collection, and minimal integration
corrections.
```

---

## 23. Standard local-agent mission

```text
Load AGENTS.md, .gpt-workflow.lock, and the exact pinned GPT Review Planner.

Apply and integrate the GPT-authored implementation. Do not redesign the feature,
weaken tests, or alter acceptance criteria.

Restore dependencies, compile the project, run all required quality gates,
correct only verified integration defects, add regression coverage for every
correction, document every deviation, and produce exact evidence.
```

---

## 24. Final principle

The quality of the result must not depend on the local agent independently discovering what GPT could already have specified or implemented.

GPT reduces the task to constrained integration and verification.

The local agent supplies environment execution and proof.

The two models must complement rather than duplicate each other.

## Patch-pack response handoff

Actionable workflow responses use the bounded contract in
[`docs/PATCH_PACK_HANDOFF.md`](docs/PATCH_PACK_HANDOFF.md). Patch-pack mode
prints plain-text `PATCH_PACK_NAME` and `SHA256_FILE_NAME` fields derived from
`manifest.patch_id`, then ends with the exact top-level `## AGENT_HANDOFF`
sentence. Prompt-only and no-action modes must say so and must not claim an
archive or runtime result. Before delivery, run
`scripts/validate-patch-pack-delivery.py`; bundled scope and evidence tools
must be byte-identical to the pinned planner tools and pass `--help`.

## Committed JSON evidence and release automation

Every new patch pack receives an immutable UTC identity:

```text
patch-<YYYYMMDD-HHMMSS>-<one-to-three-word-slug>
```

The manifest records a concise title and description, the last published target baseline tag, exact target base commit, implementation scope, stable requirement IDs, acceptance criteria, required gate definitions, and the evidence directory:

```text
.gpt-review/evidence/<baseline-release>/<patch-id>/
```

The local coding agent creates one implementation commit followed by one direct evidence-only commit containing exactly `manifest.json` and `evidence.json`. The manifest copy is byte-identical to the patch-pack manifest. The compact evidence file contains only the validated implementation SHA, requirement statuses and verifiable proofs, compact gate results, and structured deviations. It must not contain its own evidence commit SHA or repeat commands and expected scope already present in the manifest.

Each passing requirement cites implementation-commit proofs using source/test/workflow/documentation line ranges with exact snippet SHA-256, JSON pointer/value proofs, or deletion proofs. Gate commands remain in the manifest; evidence records results by gate ID. Deviations are embedded as compact JSON entries rather than a separate Markdown report.

Committed gate results are limited to facts knowable before the evidence commit:
local gates, implementation scope, evidence preparation, and implementation CI.
Evidence-head/final-head CI is external GitHub/PR metadata. The local agent
waits for and reports that result after pushing evidence, but never amends
evidence to insert its own CI run or commit SHA.

`scripts/verify-agent-evidence.py` validates the implementation diff, proof hashes, requirement and gate completeness, direct commit ancestry, byte-identical manifest preservation, and exact two-file evidence diff without rerunning project tests.

Repository versions are controlled by `VERSION`, `release-config.json`, and `scripts/release.py`. Concrete current versions are prohibited in README. The local agent prepares synchronized version files, executes quality gates, creates the release commit, waits for CI on that commit, and only then creates and explicitly pushes the immutable tag.
