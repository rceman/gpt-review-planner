# Rust checklist

Check stable edition/MSRV, Cargo features, fmt/Clippy, error boundaries,
unsafe contracts, blocking work, task ownership, cancellation, bounds,
timeouts, shutdown, SQLx provenance, secrets, and deterministic tests. Flag
detached tasks, ordinary-path unwraps, blocking executor work, startup DDL, and
unbounded input. Report evidence and exceptions.

## Review procedure and artifacts

### Identity and structure
Record toolchain/MSRV, Cargo workspace, module ownership, and planner lock.
### Dependencies and correctness
Check features, typed errors, invariants, generated query metadata, and API contracts.
### Errors, concurrency, and operations
Review unsafe contracts, task ownership, cancellation, blocking work, shutdown, and tracing.
### Security, database, and migrations
Verify input/auth bounds, secret redaction, SQLx boundaries, and Liquibase history.
### Performance and configuration
Check pool/queue budgets, timeouts, retry limits, configuration validation, and resource evidence.
### Tests, evidence, and classification
Record fmt/Clippy, unit/integration/contract commands, outputs, and rule severity.
### Exceptions
Require a scoped, approved, expiring declaration entry.

## Primary sources

[Rust](https://doc.rust-lang.org/), [Tokio](https://tokio.rs/), and
[Clippy](https://doc.rust-lang.org/clippy/).
