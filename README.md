# GPT Review Planner

Canonical workflow and tooling for a two-model software delivery process:

- **GPT** owns architecture, behavior, fixtures, tests, static review, and the principal implementation. GPT does not execute runtime quality gates.
- **The local coding agent** applies, integrates, restores dependencies, compiles, runs runtime tests, fixes narrow integration defects, and commits validation evidence.

Published versions are identified by immutable `vX.Y.Z` Git tags and GitHub Releases. The repository version is stored in [`VERSION`](VERSION) and must be changed only through [`scripts/release.py`](scripts/release.py).

For the complete reusable release procedure, read [`docs/RELEASE_PROCESS.md`](docs/RELEASE_PROCESS.md) and use [`prompts/AGENT_RELEASE_VERSION.md`](prompts/AGENT_RELEASE_VERSION.md).

## Review an attached project archive

The canonical guide is [`docs/PROJECT_ARCHIVE_REVIEW.md`](docs/PROJECT_ARCHIVE_REVIEW.md).
Use the [primary archive-review prompt](prompts/GPT_REVIEW_PROJECT_ARCHIVE.md)
for the default review-to-patch workflow, the [review-only prompt](prompts/GPT_REVIEW_PROJECT_ARCHIVE_ONLY.md)
for analysis-only work, and the [archive-preparation prompt](prompts/AGENT_PREPARE_PROJECT_ARCHIVE_FOR_REVIEW.md)
to prepare a pinned staging archive with official tooling.

Preferred invocations use immutable tag or commit URLs rather than `main`:

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

## Test-execution policy

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

```bash
bash scripts/new-patch-pack.sh \
  --baseline-release vX.Y.Z \
  --slug evidence-checker \
  --title "Committed evidence checker" \
  --description "Adds committed JSON evidence verification." \
  --target-repository owner/repository \
  --target-branch feature/example \
  --base-revision 0123456789abcdef0123456789abcdef01234567 \
  --output /path/to/output
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
