# Full-stack checklist

- MUST identify frontend/backend/database boundaries and profile.
- MUST verify generated contracts, auth, timeouts, secrets, migrations, tests,
  readiness, observability, and shutdown.
- SHOULD inspect resource budgets and deployment evidence.
- MUST report exceptions narrowly and distinguish legacy deviations from new
  violations.

Anti-patterns: frontend DB access, duplicated DTO authority, startup DDL, and
unbounded queues. Evidence: profile, manifests, routes, migrations, tests, and
CI output. Exceptions remain owner-approved.

## Review procedure and artifacts

### Identity and structure
Record profile, planner lock, commit, ownership tree, and frontend/backend/database boundaries.
### Dependencies and correctness
Check generated contracts, API compatibility, invariants, and failure classifications.
### Errors, concurrency, and operations
Review typed/public errors, cancellation, readiness, shutdown, queues, pools, and observability.
### Security, database, and migrations
Verify auth, secrets, input bounds, least privilege, Liquibase ownership, and migration evidence.
### Performance and configuration
Check timeouts, budgets, pagination, configuration validation, and deployment assumptions.
### Tests, evidence, and classification
Record unit/integration/E2E commands and results; classify findings as must, must-not, should, or informational.
### Exceptions
Require rule ID, scope, owner, migration target, expiry, and evidence location.

## Primary sources

[SvelteKit](https://svelte.dev/docs/kit), [PostgreSQL](https://www.postgresql.org/docs/),
and [Liquibase](https://docs.liquibase.com/).
