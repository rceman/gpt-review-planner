# Rust service profile

Use a clear `src/` or workspace layout with `main`, bootstrap/config/error,
domain, application, transport, and infrastructure boundaries. Use Tokio/Axum
where HTTP is needed, SQLx for PostgreSQL access, and Liquibase for schema
evolution. No frontend is required; apply Rust, resource, security, testing,
observability, API, and database rules that are relevant.

## Primary sources

[Rust](https://doc.rust-lang.org/), [Tokio](https://tokio.rs/), and
[Axum](https://docs.rs/axum/).

## Profile contract

### Capabilities and rules
Capabilities are Rust backend, generated contracts, PostgreSQL, Liquibase, shutdown, observability, and tests. Required rules cover Rust async/unsafe, Axum, SQLx, database, security, configuration, performance, testing, template, and exceptions.
### Loaded documents and structure
Load Rust, Axum, SQLx, PostgreSQL, Liquibase, API, security, testing, and structure documents. Keep `main`, domain, application, transport, and infrastructure boundaries visible.
### Template requirements
Require `src` and `engineering-profile.json`; do not add frontend or competing migration paths.
### Security, resources, testing, and operations
Review typed errors, task ownership, cancellation, pool budgets, auth, input limits, readiness, shutdown, tracing, deterministic tests, and CI evidence.
### Non-goals and exceptions
No frontend is implied; unsafe or alternate framework choices require explicit scoped exceptions.
### Review procedure and artifacts
Validate lock/declaration, derive capability rules, inspect ownership, and return findings, tests, manifests, and exception evidence.
