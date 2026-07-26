# Full-stack Go + SvelteKit profile

Use the canonical full-stack tree with Go under `services/api`. Gin/pgxpool/sqlc
owns backend boundaries; SvelteKit remains frontend/BFF only. PostgreSQL and
Liquibase are required when persistence exists. Review Go, Gin, pgx/sqlc,
TypeScript, SvelteKit, PostgreSQL, Liquibase, API, security, testing, and
template contracts.

## Primary sources

[Go](https://go.dev/doc/), [Gin](https://gin-gonic.com/), and
[SvelteKit](https://svelte.dev/docs/kit).

## Profile contract

### Capabilities and rules
Capabilities are frontend, Go backend, generated contracts, PostgreSQL, Liquibase, readiness, shutdown, observability, and tests. Required rules cover Go context, Gin, pgxpool/sqlc, database, security, configuration, testing, and template contracts.
### Loaded documents and structure
Load Go, Gin, pgx/sqlc, TypeScript, SvelteKit, PostgreSQL, Liquibase, API, security, testing, and template documents. Keep `apps/web` and `services/api` ownership explicit.
### Template requirements
Require `apps/web`, `services/api`, generated contract artifacts, and `engineering-profile.json`; forbid Prisma and competing authority.
### Security, resources, testing, and operations
Review context propagation, middleware order, pool budgets, migrations, auth, secrets, timeouts, readiness, shutdown, deterministic tests, and CI evidence.
### Non-goals and exceptions
This profile does not authorize Node backends, frontend DB access, or automatic rewrites. Exceptions are scoped, approved, and expiring.
### Review procedure and artifacts
Validate the pinned lock and declaration, derive applicable rules from capabilities, inspect boundaries, and return manifests, findings, tests, and evidence.
