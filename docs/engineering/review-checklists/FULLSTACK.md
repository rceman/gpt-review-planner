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

## Primary sources

[SvelteKit](https://svelte.dev/docs/kit), [PostgreSQL](https://www.postgresql.org/docs/),
and [Liquibase](https://docs.liquibase.com/).
