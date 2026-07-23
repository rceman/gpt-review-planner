# ChatGPT Rust Sandbox Bootstrap

## Purpose

This is the canonical artifact-acquisition path when the local coding agent
needs `rustc` in a sandbox whose shell cannot reach GitHub or
`static.rust-lang.org`. GPT may coordinate the artifact request and review the
returned evidence, but does not execute the compiler or benchmark.

Do not ask the user to download and re-upload the compiler when a successful
GitHub Actions run is available through the connected GitHub app.

## Required input

Ask for one Actions run URL from the canonical repository:

```text
https://github.com/rceman/gpt-review-planner/actions/runs/<RUN_ID>
```

The run must contain the artifact named:

```text
rustc-lite-linux-x86_64
```

A GitHub Release URL alone is insufficient because the connector can download
workflow artifacts by `artifact_id`, but it may not expose Release assets.

## Connector procedure

1. Extract `<RUN_ID>` from the URL.
2. Call `GitHub.fetch_workflow_run_artifacts` with:
   - `repo_full_name = rceman/gpt-review-planner`;
   - `run_id = <RUN_ID>`;
   - `name = rustc-lite-linux-x86_64`.
3. Reject expired artifacts and record:
   - artifact ID;
   - size;
   - Actions artifact digest;
   - head tag or branch;
   - head commit SHA.
4. Call `GitHub.download_workflow_artifact` using the returned artifact ID.
5. Give the materialized ZIP path returned by the connector, normally under
   `/mnt/data/`, to the local coding agent.
6. The local coding agent runs the benchmark helper:

```bash
python scripts/benchmark-offline-rust.py \
  --artifact-zip /mnt/data/rustc-lite-linux-x86_64.zip
```

The local agent's helper performs:

```text
artifact ZIP extraction
→ bundle SHA-256 verification
→ cold offline toolchain extraction
→ rustc and cargo version checks
→ rustc --test compilation
→ test execution
→ warm-cache compilation and test execution
```

## Direct bootstrap command for the local coding agent

When custom test commands are needed, first extract the Actions artifact ZIP,
then run:

```bash
bundle=/path/to/rustc-lite-<version>-x86_64-unknown-linux-gnu.tar.zst

bash scripts/bootstrap-rustc.sh \
  --force-managed \
  --no-network \
  --cache-dir /tmp/gpt-review-planner-rust-cache \
  --offline-bundle "$bundle" \
  -- bash -c '
    set -euo pipefail
    rustc --version
    cargo --version
    rustc --edition=2021 --test path/to/kernel.rs -o /tmp/kernel-tests
    /tmp/kernel-tests
  '
```

Use `bash -c`, not `bash -lc`. A login shell may reconstruct `PATH` and hide the
bundle compiler that `bootstrap-rustc.sh` just activated.

## Agent runtime evidence rules

- The `.sha256` sidecar must be beside the `.tar.zst` bundle.
- Verification uses the first SHA-256 token; older `v1.0.0` sidecars contain an
  absolute GitHub runner path and therefore cannot be passed directly to
  `sha256sum -c` outside CI.
- Starting with workflow `v1.0.1`, sidecars contain only the archive basename and
  are portable.
- The first run must use `--force-managed --no-network --offline-bundle` with an
  empty cache.
- The warm run must omit `--offline-bundle` and prove cache discovery.
- The agent reports ZIP extraction, cold compile/test, warm compile/test, Rust
  version, bundle size, and bundle SHA-256 separately.
- GPT records these as agent-reported evidence and does not rerun the benchmark.

## Observed `v1.0.0` baseline

Source:

```text
Actions run: 29910237409
Artifact ID: 8525559070
Artifact: rustc-lite-linux-x86_64
Head tag: v1.0.0
Head commit: b19c7abc2b7fb5f841ee3350df931bbc95227c00
Rust: 1.97.1 x86_64-unknown-linux-gnu
```

Five complete benchmark repetitions were recorded in the ChatGPT Linux sandbox
on 2026-07-22 before the current role-separation policy was adopted. They were
executed by GPT/ChatGPT and are retained only as a legacy performance baseline.
This historical execution does not comply with the current policy and must not be
repeated by GPT. Future benchmark, compiler, and test execution belongs exclusively
to the local coding agent, whose evidence GPT reviews without rerunning it.

Each historical repetition extracted the artifact ZIP, created an empty toolchain
cache, performed strict offline bootstrap, compiled and ran two Rust tests, then
repeated compile/test from the warm cache.

```text
Artifact ZIP:                           194,052,235 bytes
Inner rustc-lite bundle:                194,051,637 bytes
Bundle SHA-256:                          2d761c47fc6987ae574ece46b210e1495fe3d553c71d401c26d5da36431af02f
ZIP extraction median:                  0.121 s  (0.119–0.135 s)
Cold bootstrap + compile/test median:   1.029 s  (0.962–3.233 s)
Warm cache + compile/test median:       0.107 s  (0.100–0.121 s)
Rust tests:                             2 passed per run
```

Connector download duration is transport-controlled and was not exposed as a
local process duration. The raw measurements and provenance are stored in
`benchmarks/chatgpt-sandbox-rust-1.97.1.json`.
