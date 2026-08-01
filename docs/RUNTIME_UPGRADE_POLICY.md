# Runtime Upgrade Policy

This policy governs a runtime upgrade as one transaction over source and release identity, persisted state, configuration, artifacts, installed binaries, running processes, protocol/tool surface, readiness, health, and rollback state.

## Required phases

Every upgrade proceeds through `inspect → prepare → backup → migrate → validate → activate → verify → complete` or `rollback`. The target runtime's decoder and persisted-state preflight MUST pass before the old runtime is shut down. A preparation-only operation must say so in its title, objective, acceptance criteria, and result; it must not claim a full upgrade.

Each task declaration MUST contain installed and running versions as separate proofs and:

- source and target versions;
- exact source SHA and target release identity;
- persisted-state scope, whether migration is required, authorization, and the canonical migration entry point;
- target-decoder validation, affected processes, unchanged processes, installed-version and running-version checks;
- readiness and protocol/MCP verification;
- rollback source and trigger;
- compatibility scope and exact success criterion.

Success is impossible before activation and verification. A full upgrade cannot claim success while activation or a required side effect is pending. `remaining_risks` cannot conceal an incomplete required side effect. Installed and running versions MUST both be proven. A process declared unchanged MUST be identity-verified before and after the operation. Release rehearsal MUST use the previous production-like state.

Detached continuation cannot extend a terminal operation unless it is represented by a separate durable transaction authority. The canonical completion authority remains the workflow-v2 completion record.
