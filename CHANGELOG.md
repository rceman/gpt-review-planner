# Changelog

## Unreleased

- Add transactional runtime-upgrade, persisted-state migration, incident-response,
  direct-session, tool-contract, and chat-handoff policies.
- Add a strict runtime-upgrade task template, schema, validator, canonical prompts,
  and regression coverage for migration ordering, process identity, rollback, and
  authoritative refs.

## 2.0.0 — 2026-07-31

- Replaced dual gateway/repository completion paths with one explicit execution
  mode and a single authority per task.
- Added the compact GPT Tunnel completion contract with positional gate and
  acceptance identities.
- Added the data-only GPT Patch Pack v2 boundary; archive-controlled code is
  never executed.
- This incompatible redesign is prepared but not released or tagged.

## 1.5.0 — 2026-07-31

- Added immutable task gate contracts that mechanically generate manifest gates
  and executable gate plans, with captured gate-run identity verification.
- Added strict mismatch handling across workflow, gate, manifest, evidence, and
  verifier stages.

- Add a mandatory 10-minute bounded-run performance budget, first-check incident
  handling, durable KPI facts, rolling P50/P95 targets, and overrun follow-up.
- Record workflow efficiency alongside correctness without weakening gates or
  evidence requirements.
- Target the workflow policy addition for version 1.4.0.
- Make GPT Patch Pack v1 the only supported executable patch-pack format.
- Add isolated two-worktree replay, exact target-tree verification, bounded argv
  gates, relocatable checksums, deterministic archives, and rollback-safe apply.
- Remove legacy directory packs, overlays, transform runners, instruction aliases,
  format negotiation, and compatibility readers.
- Require explicit authorization for every compatibility or migration behavior.
- Add manifest and evidence compatibility declarations plus CI/release self-tests.
- Require a durable gateway-hub plan record before every executable task bundle.
- Replace duplicated gateway terminal Markdown/JSON outputs with one strict `agent-result.json` contract.
- Add a generated `complete-task` finalizer protocol for every success, revision, or failure outcome.
- Add dependency-free schema validation and regression coverage for gateway terminal results.

## 1.3.0 — 2026-07-28

- Made `AGENT_HANDOFF.md` the canonical mandatory executable patch-pack entry point and deprecated `AGENT_PROMPT.md` as a byte-identical one-release compatibility alias.
- Added stable JSON output schemas and deterministic error codes for semantic and delivery validation.
- Added `manual-download`, `gateway-task-bundle`, `prompt-only`, and `no-action` delivery modes without moving transport ownership into the planner.
- Fixed evidence preparation to accept exactly two generated evidence files as untracked or staged additions while preserving the direct-child evidence-only commit contract.
- Added gateway interoperability and structured JSON/Markdown/YAML ownership policies, a complete reference fixture, and focused regression coverage.
- Added a normative English-only local-agent communication contract covering
  handoffs, prompts, execution reports, managed agent instructions, and tests.
- Added a normative post-merge remote-branch cleanup and finalization contract.
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
