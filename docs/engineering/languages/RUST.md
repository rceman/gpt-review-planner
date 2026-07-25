# Rust baseline

## Scope

Rust is canonical for APIs, workers, WebSockets, resource-sensitive services,
and authoritative domain logic. Use stable Rust, explicit edition/MSRV, Cargo
workspace boundaries, clear modules/crates, minimal dependencies/features, and
review feature unification.

## Rules

Use `cargo fmt` and Clippy’s correctness/all categories with warnings denied or
an equivalent gate; do not enable all restriction lints blindly. `unsafe` is
narrow, documented with a safety contract, and tested. Ordinary request/data
paths do not use `unwrap`/`expect`; startup invariants need justification.
Domain boundaries use typed errors; binary edges add context. Never block an
async executor. Own spawned tasks, cancellation, bounded channels, graceful
shutdown, timeouts, body/message limits, and concurrency limits explicitly.
Avoid needless cloning/allocation and global mutable state. Use deterministic,
property, or fuzz tests when parser/protocol risk justifies them. No secrets in
logs; Liquibase owns schema evolution and SQLx is the query integration.

## Review evidence

Check Cargo manifests, lint configuration, task ownership, error paths,
timeouts, shutdown tests, `.sqlx` provenance when used, and CI commands.

## Primary sources

[Rust API Guidelines](https://rust-lang.github.io/api-guidelines/),
[Cargo](https://doc.rust-lang.org/cargo/), [Tokio](https://tokio.rs/),
[Clippy](https://doc.rust-lang.org/clippy/), and [SQLx](https://docs.rs/sqlx/).

Anchors: `RUST-ERROR-001` `RUST-ASYNC-001` `RUST-UNSAFE-001`.
