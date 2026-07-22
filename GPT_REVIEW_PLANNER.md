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

The objective is to minimize both:

1. time spent by GPT installing dependencies, compiling full workspaces, launching browsers, databases, containers, or long-running test suites;
2. tokens spent by the local agent rediscovering architecture, inventing behavior, writing routine code, or interpreting vague prose.

The expected operating model is:

```text
GPT provides intelligence and most of the implementation.
The local agent provides environment execution and evidence.
```

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
- performing all reasonable dependency-free validation;
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

GPT reproduces the defect through a test or fixture, identifies the root cause, writes the fix, and delegates environment validation.

### 5.4 Refactor

GPT first captures existing behavior with characterization tests, then prepares the structural change. The local agent proves behavioral equivalence.

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

### Phase 6 — Dependency-free validation

Run every inexpensive check available without dependency restoration.

Examples:

```bash
# Rust
rustfmt --check path/to/file.rs
rustc --edition=2021 --test path/to/standalone_kernel.rs

# Python
python -m unittest discover
python -m compileall .

# JavaScript
node --check path/to/file.js
node --test

# PHP
php -l path/to/file.php

# Repository
git diff --check
find . -name '*Zone.Identifier*' -o -name '*Zone.Identifier'
```

Also scan for placeholders, missing exports, broken fixture paths, accidental dependency changes, secrets, machine-specific paths, and out-of-scope files.

#### Fast Rust compiler bootstrap

If `rustc` is missing, do not immediately delegate standalone Rust validation or
install the full project environment. Use the canonical bootstrap first:

```bash
bash scripts/bootstrap-rustc.sh
```

For a compile-and-test operation in one prepared environment:

```bash
bash scripts/bootstrap-rustc.sh -- bash -c '
  rustc --edition=2021 --test path/to/kernel.rs -o /tmp/kernel-tests
  /tmp/kernel-tests
'
```

The bootstrap must use this priority:

1. reuse an existing working compiler when available;
2. otherwise reuse a previously extracted workflow-managed cache;
3. otherwise use an explicit or repository-bundled offline `rustc-lite` archive;
4. otherwise use an explicitly configured GitHub Release asset URL;
5. only then download the official target-specific `rustup-init`;
6. verify every downloaded or supplied artifact with SHA-256;
7. install network toolchains with the official `minimal` profile;
8. honor a project `rust-toolchain.toml` or `rust-toolchain` when rustup mode is requested.

Do not commit Rust compiler payloads to ordinary Git history. GitHub Actions
must build them from the official minimal toolchain and publish them as
versioned workflow artifacts and GitHub Release assets. A self-contained patch
or project archive may include the matching bundle when a truly zero-network
sandbox is required; its SHA-256 sidecar and provenance manifest are mandatory.

See `docs/FAST_RUSTC_BOOTSTRAP.md` for commands, cache layout, limitations, and
toolchain-selection rules.

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

Example validation:

```bash
rustc --edition=2021 --test damage_kernel.rs -o /tmp/damage-kernel-tests
/tmp/damage-kernel-tests
```

This validates domain behavior without claiming full workspace integration.

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
- `VALIDATION_REPORT.md`: exact checks GPT executed and did not execute.
- `manifest.json`: machine-readable scope, risks, required gates, and workflow pin.

---

## 10. Confidence classification

### GREEN — locally validated

Examples:

- standalone native tests passed;
- reference oracle passed;
- fixtures validated;
- syntax and formatting checked;
- generated patch checked.

GREEN does not imply full workspace integration unless that workspace was actually built and tested.

### YELLOW — complete implementation requiring environment validation

Examples:

- crate adapter;
- async wiring;
- route;
- migration;
- browser component;
- serialization adapter;
- workspace integration test.

YELLOW code must still be complete, not a placeholder.

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

Every material deviation must record:

```text
Deviation ID:
Original implementation:
Observed failure:
Repository evidence:
Changed implementation:
Behavioral impact:
Tests proving correctness:
Approval required:
```

A successful build is not sufficient justification for a behavioral deviation.

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

- real behavior executed;
- assertions meaningful;
- negative and regression cases present;
- deterministic;
- not over-mocked;
- capable of failing when implementation is broken.

### Deviations

Each deviation must be accepted, corrected, or rejected.

---

## 15. Quality gates and Definition of Done

A task is complete only when applicable gates pass:

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
9. final result reviewed;
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

Do not install dependencies or run expensive full-project gates unless necessary.
Perform every available dependency-free validation.

Leave the local agent only repository integration, compilation, runtime test
execution, evidence collection, and minimal integration corrections.
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
