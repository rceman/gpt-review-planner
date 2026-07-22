# Changelog

All notable changes to this workflow are documented here.

## 1.0.1 — 2026-07-22

- Fixed release checksum sidecars so they contain only the bundle basename and
  work with `sha256sum -c` outside the GitHub runner workspace.
- Added `rustc-lite-manifest.json` to Actions artifacts and GitHub Releases.
- Added explicit CI validation for portable release metadata.
- Replaced `bash -lc` bootstrap examples with `bash -c`; login shells can replace
  `PATH` and hide the prepared offline compiler.
- Added a bootstrap guard that rejects known Bash login-shell commands.
- Added a dependency-free benchmark helper for downloaded Actions artifacts.
- Added the canonical ChatGPT GitHub-connector procedure for downloading an
  artifact by Actions run URL and `artifact_id`.
- Added a five-run ChatGPT sandbox benchmark with provenance and cold/warm timing.

## 1.0.0 — 2026-07-22

- Initial normative GPT/local-agent responsibility model.
- Added Option A project integration through `AGENTS.md` and `.gpt-workflow.lock`.
- Added idempotent `setup.sh` and `update.sh`.
- Added Executable Patch Pack templates.
- Added machine-readable schemas.
- Added dependency-free validators and tests.
- Added a worked Rust domain-feature example.
- Added a fast cached `rustc` bootstrap using the official minimal rustup profile.
- Added GitHub Actions generation of verified offline `rustc-lite` bundles.
- Added strict zero-network bundle extraction and cache reuse to `bootstrap-rustc.sh`.
- Documented why compiler binaries must not be committed to repositories or patch packs.
