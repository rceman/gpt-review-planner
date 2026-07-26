# Full-stack Rust + SvelteKit profile

Use `apps/web`, `services/api`, `db`, `contracts`, operations/security docs,
integration/E2E tests, and `engineering-profile.json`. Rust/Axum owns backend
domain logic; SvelteKit is frontend/BFF only. PostgreSQL and Liquibase are
required when persistence exists. Review the Rust, Axum, SQLx, TypeScript,
SvelteKit, PostgreSQL, Liquibase, API, security, testing, and template contracts.

## Primary sources

See the linked language/framework/database documents and
[SvelteKit](https://svelte.dev/docs/kit).

## Profile contract

### Capabilities and rules
Capabilities are frontend, Rust backend, generated contracts, PostgreSQL, Liquibase, readiness, shutdown, observability, and tests. Required rules are stack, API, security, bounds, configuration, database, Axum, SQLx, and testing rules; recommended rules cover contracts and operations; forbidden rules cover Node backend, startup migration, and SvelteKit domain authority.
### Loaded documents and structure
Load the Rust, Axum, SQLx, TypeScript, SvelteKit, PostgreSQL, Liquibase, API, security, testing, and template documents. Expected structure separates `apps/web`, `services/api`, `db`, `contracts`, and operations.
### Template requirements
The template must declare the profile, required capabilities, generated contracts, and service/frontend ownership paths.
### Security, resources, testing, and operations
Review auth, secret boundaries, request limits, pool budgets, readiness, shutdown, tracing, deterministic unit/integration/E2E tests, and CI evidence.
### Non-goals and exceptions
This profile does not authorize frontend database access, automatic rewrites, or unrecorded exceptions. Exceptions require owner, scope, rule ID, migration metadata, and expiry.
### Review procedure and artifacts
Resolve the pinned planner, validate the declaration and lock, inspect applicable rules, report findings by rule ID, and return the archive manifest, diff, tests, and exception evidence.
