# Stack policy

## Scope

This document selects the canonical low-overhead stack; it does not prohibit a
legacy system from continuing under a valid declaration. Resource priority is
idle/peak RAM, CPU, cold start, latency, attack surface, bootstrap cost, then
ecosystem convenience.

## Canonical choices

The frontend is TypeScript + SvelteKit. The primary backend is Rust + Tokio +
Axum + Tower + SQLx. The secondary backend is Go + Gin + pgxpool + sqlc. The
database is PostgreSQL and Liquibase is the schema authority.

Production Node.js/TypeScript services, workers, daemons, direct frontend DB
access, and TypeScript migration authorities are `MUST NOT` by default. Thin
SvelteKit BFF behavior may delegate to Rust or Go but cannot own domain truth.
Go requires a selected profile or written exception. Python production services
require a project exception; Python tools, tests, automation, prototypes, and
data tasks are allowed. These are forbidden by the canonical policy unless a
specific rule permits a narrow exception.

## Evidence and anti-patterns

Review package manifests, entrypoints, database clients, migration directories,
deployment files, and generated clients. Flag Express/Nest/Fastify-style
production backends, Prisma/Drizzle/Alembic schema authority, startup DDL, and
browser database credentials. Do not propose a rewrite solely from a default
tree mismatch; establish scope and owner intent first.

## Primary sources

[SvelteKit](https://svelte.dev/docs/kit), [Axum](https://docs.rs/axum/),
[Gin](https://gin-gonic.com/), [pgx](https://pkg.go.dev/github.com/jackc/pgx),
[PostgreSQL](https://www.postgresql.org/docs/), and
[Liquibase](https://docs.liquibase.com/).
