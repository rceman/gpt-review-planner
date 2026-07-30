# GPT Review Planner

Start with the [procedure index](docs/PROCEDURE_INDEX.md) for workflow roles, contracts, prompts, statuses, and next transitions. Use the [agent reporting contract](docs/AGENT_REPORTING.md) for compact final reports.

Canonical workflow and tooling for a two-model software delivery process:

- **GPT** owns architecture, behavior, fixtures, tests, static review, and the principal implementation. GPT does not execute runtime quality gates.
- **The local coding agent** applies, integrates, restores dependencies, compiles, runs runtime tests, fixes narrow integration defects, and commits validation evidence.

Published versions are identified by immutable `vX.Y.Z` Git tags and GitHub Releases. The repository version is stored in [`VERSION`](VERSION) and must be changed only through [`scripts/release.py`](scripts/release.py).

For the complete reusable release procedure, read [`docs/RELEASE_PROCESS.md`](docs/RELEASE_PROCESS.md) and use [`prompts/AGENT_RELEASE_VERSION.md`](prompts/AGENT_RELEASE_VERSION.md).

The [engineering baseline](docs/engineering/README.md) defines the canonical
stack, profiles, exceptions, and review checklists. Validate the registry with
`python3 scripts/validate-engineering-catalog.py` and a project declaration with
`scripts/validate-project-engineering-profile.py`.

The [bounded review closure protocol](docs/REVIEW_CLOSURE_PROTOCOL.md) prevents
recursive blocker expansion after an approved scope. Validate its machine
contract with `python3 scripts/validate-review-closure.py`; implementation-result
reviews use delta mode and stop when the `MERGE_READY` conditions are satisfied.

After merge, follow the [post-merge branch cleanup contract](docs/POST_MERGE_BRANCH_CLEANUP.md)
to verify exact-SHA integration and safely delete the merged remote feature branch.

All GPT-to-agent handoffs and local-agent execution reports use English regardless
of the owner's conversation language. See the normative
[agent communication language contract](docs/AGENT_COMMUNICATION_LANGUAGE.md).

## Review an attached project archive

The canonical guide is [`docs/PROJECT_ARCHIVE_REVIEW.md`](docs/PROJECT_ARCHIVE_REVIEW.md).
Use the [review-and-implement prompt](prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md)
for the default approval-gated workflow, the [review-only prompt](prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md)
for analysis-only work, and the [archive-preparation prompt](prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md)
to prepare a pinned staging archive with official tooling.

Preferred everyday archive preparation uses an immutable link plus owner
objective; omitted source, staging mode, downstream workflow, full scope, and
external output path use safe defaults:

```text
Prepare review archive using:
https://github.com/rceman/gpt-review-planner/blob/vX.Y.Z/prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md

We want to remove all AnyDesk occurrences because we are switching to RustDesk only.
```

This means a full review with the migration objective as a mandatory overlay,
not migration-only review. Use explicit restrictive wording such as `Limit the
review strictly to the AnyDesk-to-RustDesk migration.` to select objective-only
scope. Preparer observations and questions are untrusted hints that GPT must
independently verify. In staging, the immutable methodology URL explicitly
selects the staged workflow: a matching source lock is preserved, while an older
valid lock is reconciled only in the temporary staging copy using official
tooling. The source lock and `AGENTS.md` remain unchanged. Integrate-source
requires separate authorization to modify source.

Expanded invocations remain supported for automation and unusual cases.
immutable tag or commit URLs are required; do not use `main`:

```text
Review the attached project archive using this immutable guide:
<IMMUTABLE_ARCHIVE_REVIEW_PROMPT_URL>
Task objective: <OWNER_TASK_OBJECTIVE_OR_FULL_REVIEW>
Stop after the proposed exact patch scope and wait for my approval.
```

Raw archives may use an immutable prompt URL without a lock; recurring projects
should use prepared archives with an officially generated `.gpt-workflow.lock`.
Already integrated archives use their existing lock. The owner objective controls
whether review focuses on bugs, refactoring, performance, dependencies, security,
tests, or a specific change.
One universal preparation prompt creates the same complete archive for both
downstream workflows and adds `.gpt-review/archive-manifest.json`; workflow
selection never changes archive contents.
Archive setup always requires an owner-selected immutable `--version REF`;
optional `--commit SHA` must match that REF and cannot replace it.

## Test-execution policy

Before running the complete gate suite, check the [host prerequisites](docs/HOST_PREREQUISITES.md), including `python3 -m pytest`.

GPT may analyze repositories statically, write specifications, fixtures, production code, and tests, and prepare patch-pack artifacts. Runtime validation is not executed by GPT.

The local coding agent owns dependency restoration, formatting, compilation, linting, unit/integration/E2E tests, benchmarks, runtime smoke tests, narrow integration fixes, regression coverage, and exact committed JSON evidence.

## Repository contents

```text
GPT_REVIEW_PLANNER.md       Normative workflow
VERSION                     Canonical repository version
release-config.json         Version-bearing file registry
setup.sh                    Install the workflow pin into a project
update.sh                   Update an existing project pin
templates/                  Executable Patch Pack templates
schemas/                    Patch-manifest and evidence schemas
examples/                   Worked examples
prompts/                    Reusable GPT and local-agent prompts
scripts/                    Release, bootstrap, archive, and validation tools
tests/                      Dependency-free tests
.gpt-review/evidence/       Committed patch manifests and JSON agent evidence
```

## Install into a project

Choose an immutable published tag:

```bash
RELEASE_TAG="vX.Y.Z"

bash setup.sh \
  --project /path/to/project \
  --version "$RELEASE_TAG"
```

For a temporary clone:

```bash
RELEASE_TAG="vX.Y.Z"
tmp_dir="$(mktemp -d)"

git clone --depth 1 --branch "$RELEASE_TAG" \
  https://github.com/rceman/gpt-review-planner.git "$tmp_dir"

bash "$tmp_dir/setup.sh" \
  --project /path/to/project \
  --version "$RELEASE_TAG"
```

## Update a project

```bash
RELEASE_TAG="vX.Y.Z"
bash update.sh --project /path/to/project --version "$RELEASE_TAG"
```

## Verify setup

```bash
python scripts/validate-project-integration.py /path/to/project
```

## Create a patch pack

GPT Patch Pack v1 is the only executable format. Read the [patch-pack handoff contract](docs/PATCH_PACK_HANDOFF.md) and the
[reusable creation prompt](prompts/GPT_CREATE_PATCH_PACK.md) for canonical
`AGENT_HANDOFF.md`, archive names, semantic JSON validation, delivery modes,
and final handoff syntax. `AGENT_PROMPT.md` is not a second instruction source;
when retained for one-release compatibility it must be byte-identical to the
canonical handoff.

Gateway protocol-v2 interoperability is defined by
[`docs/GATEWAY_INTEROPERABILITY.md`](docs/GATEWAY_INTEROPERABILITY.md). JSON is
the canonical machine format, Markdown is the canonical human/agent instruction
format, and YAML is not accepted as a wire artifact; see
[`docs/STRUCTURED_FORMAT_POLICY.md`](docs/STRUCTURED_FORMAT_POLICY.md).

Gateway task continuity and terminal completion are defined by
[`docs/GATEWAY_TASK_PROTOCOL.md`](docs/GATEWAY_TASK_PROTOCOL.md). GPT commits a
durable plan record before an executable task bundle. New gateway-managed agents
write one strict `agent-result.json` and invoke one generated `complete-task`
command; interactive session text is never the terminal result.

```bash
bash scripts/new-patch-pack.sh \
  --repo /path/to/target \
  --repository owner/repository \
  --accepted-origin-url git@github.com:owner/repository.git \
  --branch feature/example \
  --base-commit 0123456789abcdef0123456789abcdef01234567 \
  --remote origin \
  --remote-ref refs/remotes/origin/feature/example \
  --baseline-release vX.Y.Z \
  --slug evidence-checker \
  --title "Committed evidence checker" \
  --description "Adds committed JSON evidence verification." \
  --changes-patch /path/to/changes.patch \
  --agent-task /path/to/AGENT_TASK.md \
  --requirements /path/to/requirements.json \
  --gates /path/to/gates.json \
  --output-directory /path/to/output \
  --planner-commit <planner-sha>
```

The generator assigns a UTC timestamp and creates a patch ID such as:

```text
patch-YYYYMMDD-HHMMSS-evidence-checker
```

The resulting evidence directory contains exactly:

```text
.gpt-review/evidence/vX.Y.Z/patch-YYYYMMDD-HHMMSS-evidence-checker/
├── manifest.json
└── evidence.json
```

See [`docs/PATCH_PACK_FORMAT.md`](docs/PATCH_PACK_FORMAT.md) and [`docs/AGENT_EVIDENCE.md`](docs/AGENT_EVIDENCE.md).

Verify or explicitly apply:

```bash
python3 scripts/gpt-patch-pack-runner-v1.py \
  --archive /path/to/<patch_id>.tar.gz \
  --archive-sha256 <sha256> \
  --repo /path/to/target \
  --apply
```

## Release workflow

```bash
python scripts/release.py check
python scripts/release.py prepare X.Y.Z
# Local agent runs every required quality gate.
python scripts/release.py commit
# Push the release commit and wait for CI.
python scripts/release.py tag
# Push the created tag explicitly.
```

See [`docs/RELEASE_PROCESS.md`](docs/RELEASE_PROCESS.md) and [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md).

## Fast standalone Rust validation

Runtime execution belongs to the local coding agent:

```bash
bash scripts/bootstrap-rustc.sh
```

See [`docs/FAST_RUSTC_BOOTSTRAP.md`](docs/FAST_RUSTC_BOOTSTRAP.md).
Remote CI is a capability-dependent gate, not a universal repository requirement. Repository visibility alone MUST NOT decide whether remote CI is required. When remote CI is unavailable or intentionally disabled, mandatory local runtime gates remain authoritative.
