# Changelog

## Unreleased

- Added a bounded, machine-checkable patch-pack handoff contract and delivery validator.
- Added a bounded review and closure protocol with acceptance-contract scope
  locking, evidence-based blocker thresholds, delta reviews, and explicit stop
  conditions.
- Added a machine-readable closure contract, dependency-free validator, prompt
  integration, and regression tests preventing recursive blocker expansion.

## 1.2.0 — 2026-07-26

- Added the opinionated engineering baseline for canonical stacks, languages,
  frameworks, databases, profiles, and review checklists.
- Added machine-readable rule/catalog registries, project exceptions, schemas,
  and dependency-free validators.
- Integrated engineering-profile validation into archive review, preparation,
  and managed AGENTS instructions, with a template repository conformance
  contract.
- Expanded the engineering knowledge base with normative language, framework,
  database, security, testing, and operational rules.
- Added explicit rule anchors, primary-source freshness metadata, schemas,
  capability-aware profiles, and dependency-free validators.
- Clarified archive preparation ordering and the declaration/lock/capability
  contract used by downstream agents.
- Closed engineering-baseline review gaps with derived applicability coverage,
  strict declaration identity checks, source-domain allowlists, and schema/example parity.
- Expanded all profile and review-checklist documents with operational evidence,
  exception, security, resource, and review-procedure contracts.
- Align engineering-profile validation with the official `installed_at` lock
  field and support exact commit-pinned workflow versions.

## 1.1.1 — 2026-07-25

- Added compact immutable-link-plus-objective archive preparation.
- Made full review the default with owner objectives as mandatory overlays.
- Added bounded preparer observations/questions to the archive manifest.
- Added backward-compatible validator support for the optional review context.
- Reconciled staged locks against the immutable methodology URL and rejected the complete ASCII control range in preparer context.

## 1.1.0 — 2026-07-25

- Added reusable attached-project archive review and review-only prompts.
- Added task-objective-aware review scope and staged archive preparation with generated workflow locks.
- Added exact commit-pinned archive-review prompt links to managed project integration.
- Unified preparation into one prompt for both GPT workflows and added provenance metadata without changing archive contents by downstream mode.
- Hardened portable archive roots, exact setup version/commit invocation, and complete generated release-agent rules.

## 1.0.2 — 2026-07-24

- Added timestamped patch identities with stable requirement and gate IDs.
- Replaced Markdown agent-result/deviation evidence with compact committed `evidence.json`.
- Added implementation-commit proof validation using paths, lines, snippet hashes, JSON pointers, and deletion checks.
- Added dependency-free release automation for synchronized version files, release commits, and tags.
- Removed concrete current-version literals from README and generalized release documentation.
- Removed obsolete pre-contract evidence instead of reconstructing or migrating it.


All notable changes to this workflow are documented here.

## 1.0.1 — 2026-07-23

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
- Hardened Bash login-shell detection across option ordering and option arguments.
- Added exact manifest/patch/overlay/delete/final-diff scope verification.
- Added mandatory `DEVIATIONS.md` reports to generated patch packs.
- Added CI verification of release-manifest SHA-256 and size metadata.
- Made `changes.patch` path extraction Unicode- and whitespace-safe by delegating
  parsing to `git apply --numstat -z`.
- Made final scope verification operation-aware: created, modified, and deleted
  manifest sets are checked independently, including rename and copy semantics.

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
