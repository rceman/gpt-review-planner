# Changelog

All notable changes to this workflow are documented here.

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
