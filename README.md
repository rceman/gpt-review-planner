# GPT Review Planner

Canonical workflow and tooling for a two-model software delivery process:

- **GPT** owns architecture, behavior, fixtures, tests, review, and the principal implementation.
- **The local coding agent** applies, integrates, compiles, runs runtime tests, fixes narrow integration defects, and produces evidence.

Current version: **1.0.1**

For first-time GitHub publication, follow [`UPLOAD_TO_GITHUB.md`](UPLOAD_TO_GITHUB.md).

## Repository contents

```text
GPT_REVIEW_PLANNER.md       Normative workflow
setup.sh                    Install the workflow pin into a project
update.sh                   Update an existing project pin
schemas/                    JSON schemas
templates/                  Executable Patch Pack templates
examples/                   Worked examples
prompts/                    Reusable GPT and local-agent prompts
scripts/                    Bootstrap, archive, and validation tools
tests/                      Dependency-free tests
```


## First publication on GitHub

After uploading this archive's contents to the empty repository:

1. Commit the files to `main`.
2. Wait for both GitHub Actions workflows to pass:
   - `Validate`;
   - `Build Offline Rust Toolchain`.
3. Download the `rustc-lite-linux-x86_64` artifact once to verify it exists.
4. Create and push tag `v1.0.1` from the validated commit.
5. The tag workflow creates or updates the GitHub Release and attaches the
   offline Rust bundle, portable SHA-256 sidecar, and release manifest.
6. Use `v1.0.1` in project setup commands.

The default setup command resolves the tag to its exact commit SHA and stores
both values in `.gpt-workflow.lock`.

## Install into a project

Clone this repository, then run:

```bash
bash setup.sh --project /path/to/project --version v1.0.1
```

This creates or updates:

```text
/path/to/project/AGENTS.md
/path/to/project/.gpt-workflow.lock
```

The workflow document itself is not copied into the project.

### Install from a temporary clone

```bash
tmp_dir="$(mktemp -d)"
git clone --depth 1 --branch v1.0.1 \
  https://github.com/rceman/gpt-review-planner.git "$tmp_dir"

bash "$tmp_dir/setup.sh" \
  --project /path/to/project \
  --version v1.0.1
```

## Update a project

```bash
bash update.sh --project /path/to/project --version v1.1.0
```

`update.sh` reads the canonical repository from the existing lock file unless `--repository` is supplied.

## Verify setup

```bash
python scripts/validate-project-integration.py /path/to/project
```

## Create a patch pack

```bash
bash scripts/new-patch-pack.sh \
  PROJECT-FEATURE-001 \
  /path/to/output
```

Then fill in the generated files and validate exact scope:

```bash
python scripts/validate-patch-pack.py \
  /path/to/output/PROJECT-FEATURE-001
```

The validator compares `manifest.json` with `changes.patch`, `overlay/`, and
`delete-paths.txt`. After the agent finishes, the pack's
`scripts/verify-agent-result.sh` also compares the final repository diff with the
same manifest scope and requires an explicit `DEVIATIONS.md` status.

## Fast standalone Rust validation

The bootstrap supports both online machines and zero-network sandboxes.

Reuse an installed compiler, extracted cache, repository bundle, GitHub Release
asset, or official rustup fallback:

```bash
bash scripts/bootstrap-rustc.sh
```

Strict offline use with a downloaded Actions artifact:

```bash
bash scripts/bootstrap-rustc.sh \
  --force-managed \
  --no-network \
  --offline-bundle /path/to/rustc-lite-*.tar.zst \
  -- bash -c '
    rustc --version
    rustc --edition=2021 --test path/to/kernel.rs -o /tmp/kernel-tests
    /tmp/kernel-tests
  '
```

GitHub Actions builds the bundle from the official Rust minimal profile and
proves that the bundle can compile and execute the repository's standalone Rust
example with network access disabled at the bootstrap layer. Compiler binaries
are stored as Actions artifacts and GitHub Release assets, not committed to Git.
See [`docs/FAST_RUSTC_BOOTSTRAP.md`](docs/FAST_RUSTC_BOOTSTRAP.md).

For ChatGPT sandboxes whose shell cannot reach GitHub, provide the successful
`Build Offline Rust Toolchain` Actions run URL. GPT can download the named
workflow artifact through the connected GitHub integration and run:

```bash
python scripts/benchmark-offline-rust.py \
  --artifact-zip /mnt/data/rustc-lite-linux-x86_64.zip
```

The exact connector procedure and measured baseline are documented in
[`docs/CHATGPT_RUST_SANDBOX_BOOTSTRAP.md`](docs/CHATGPT_RUST_SANDBOX_BOOTSTRAP.md).

## Run repository tests

```bash
python -m unittest discover -s tests -v
```

## Versioning

The active document name is always `GPT_REVIEW_PLANNER.md`.

Releases are pinned with semantic-version Git tags:

```text
v1.0.0
v1.1.0
v2.0.0
```

Projects pin both the tag and the exact commit in `.gpt-workflow.lock`.

## GitHub web upload note

When files are uploaded through github.com, executable bits may not be preserved. Run shell scripts with `bash`:

```bash
bash setup.sh ...
bash update.sh ...
```
