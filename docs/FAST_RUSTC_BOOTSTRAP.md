# Fast and Offline `rustc` Bootstrap

## Objective

Provide a working Rust compiler for standalone `rustc --test` validation with
minimal setup time and without restoring project dependencies.

The same script supports:

- normal developer machines;
- local agents with internet access;
- repeated cached runs;
- ChatGPT or CI sandboxes with no shell network access.

## Bootstrap priority

`scripts/bootstrap-rustc.sh` uses this order:

1. existing working `rustc`;
2. previously extracted toolchain in the persistent cache;
3. explicit `--offline-bundle` archive;
4. compatible archive under repository `toolchains/`;
5. explicit `--bundle-url` plus its `.sha256` sidecar;
6. official target-specific `rustup-init` with the `minimal` profile.

Use `--force-managed` to ignore a system compiler. Use `--no-network` or
`GPT_RUSTC_NO_NETWORK=1` to prove that no download fallback is possible.

## Why compiler payloads are not committed

Rust compiler payloads are large, host-specific, and updated frequently.
Ordinary Git history is the wrong distribution mechanism.

The repository instead contains:

- a reproducible builder script;
- GitHub Actions automation;
- SHA-256 verification;
- a strict offline extraction path.

GitHub Actions publishes bundles as:

- a 90-day downloadable workflow artifact on relevant `main` commits;
- persistent GitHub Release assets on `v*` tags.

A self-contained project or patch archive may include the bundle when its target
sandbox cannot reach GitHub or Rust infrastructure.

## Bundle contents

The builder installs the official Rust `minimal` profile into an isolated
`RUSTUP_HOME`, then packages the resolved sysroot. The bundle contains:

- `rustc`;
- host `rust-std`;
- `cargo`;
- Rust license and toolchain metadata;
- `manifest.json` inside the sysroot recording version, host, commit, and provenance format.

The release artifact also contains `rustc-lite-manifest.json` beside the bundle.
It records the exact archive basename, portable checksum filename, SHA-256, size,
Rust release, host, and compiler commit.

It intentionally omits rustfmt, Clippy, rust-docs, extra targets, and project
Cargo dependencies.

## GitHub Actions behavior

`.github/workflows/build-offline-rust.yml` runs when:

- relevant bootstrap files change on `main`;
- a `v*` tag is pushed;
- it is started manually.

The workflow:

1. creates an isolated official minimal toolchain;
2. packages `rustc-lite-<version>-<host>.tar.zst`;
3. creates a portable SHA-256 sidecar containing only the archive basename;
4. creates `rustc-lite-manifest.json` with machine-readable release metadata;
5. validates the sidecar using `sha256sum -c` from inside `dist/`;
6. uses `bootstrap-rustc.sh --no-network --offline-bundle ...` with a fresh cache;
7. compiles and runs the standalone Rust example;
8. uploads the bundle, sidecar, and manifest as an Actions artifact;
9. on a version tag, creates or updates the GitHub Release and attaches them.

## Strict offline use

After downloading and extracting the GitHub Actions artifact ZIP:

```bash
bundle=/path/to/rustc-lite-<version>-x86_64-unknown-linux-gnu.tar.zst

GPT_RUSTC_NO_NETWORK=1 bash scripts/bootstrap-rustc.sh \
  --force-managed \
  --no-network \
  --cache-dir /tmp/gpt-review-planner-rust \
  --offline-bundle "$bundle" \
  -- bash -c '
    rustc --version
    cargo --version
    rustc --edition=2021 --test path/to/kernel.rs -o /tmp/kernel-tests
    /tmp/kernel-tests
  '
```

The `.sha256` file must be next to the archive and named:

```text
<archive-name>.sha256
```

Use `bash -c`, not `bash -lc`, for a compound command. A Bash login shell may
reconstruct `PATH` and hide the compiler prepared by `bootstrap-rustc.sh`.
The bootstrap rejects known Bash login-shell invocations for this reason.

The first offline invocation verifies and extracts the archive. Later runs reuse
the extracted cache without reading or downloading the archive again.


## ChatGPT Actions-artifact path

When the shell cannot resolve GitHub but the connected GitHub app is available,
provide a successful Actions run URL:

```text
https://github.com/rceman/gpt-review-planner/actions/runs/<RUN_ID>
```

GPT should fetch the artifact named `rustc-lite-linux-x86_64`, download it by
`artifact_id`, and then run:

```bash
python scripts/benchmark-offline-rust.py \
  --artifact-zip /mnt/data/rustc-lite-linux-x86_64.zip
```

See [`CHATGPT_RUST_SANDBOX_BOOTSTRAP.md`](CHATGPT_RUST_SANDBOX_BOOTSTRAP.md) for
the exact connector calls, validation gates, and the observed benchmark.

## Repository-bundled use

For a completely self-contained uploaded archive, place both files under:

```text
toolchains/
├── rustc-lite-<version>-<host>.tar.zst
└── rustc-lite-<version>-<host>.tar.zst.sha256
```

Then run:

```bash
GPT_RUSTC_NO_NETWORK=1 bash scripts/bootstrap-rustc.sh \
  --force-managed \
  --no-network \
  -- rustc --version
```

The compiler payload must not be committed to Git; `toolchains/` is a staging
location for downloaded or uploaded sandbox archives.

## Online release-asset use

A local agent with GitHub access may pass a Release asset URL:

```bash
bash scripts/bootstrap-rustc.sh \
  --bundle-url '<release-asset-url>' \
  --force-managed \
  -- rustc --version
```

The script downloads both the bundle and `<URL>.sha256`, verifies them, extracts
once, and reuses the cache later.

## Building manually

```bash
bash scripts/build-offline-rust-bundle.sh \
  --toolchain stable \
  --output-dir dist
```

This requires `rustup`, `tar`, `zstd`, and Python 3 on the builder machine.

## Cache layout

```text
${XDG_CACHE_HOME:-$HOME/.cache}/gpt-review-planner/
├── toolchains/   extracted offline bundles
├── downloads/    verified Release-asset downloads
├── rustup/       network fallback toolchains
├── cargo/        rustup shims
└── bin/          verified rustup-init installer
```

## Scope

This bootstrap is intended for:

- standard-library-only modules;
- standalone unit tests compiled with `rustc --test`;
- domain kernels and algorithms;
- early syntax and behavior validation.

It does not replace full project integration when the task requires Cargo
registry dependencies, Clippy, rustfmt, extra targets, native libraries, WASM,
Docker services, databases, browsers, or workspace-wide builds.
