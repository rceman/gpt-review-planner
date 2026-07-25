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

<a id="rust-error-001"></a>
<a id="rust-async-001"></a>
<a id="rust-unsafe-001"></a>

## Operational review matrix

### Canonical use cases
Bounded services, workers, domain logic, and infrastructure with explicit ownership.
### Forbidden/non-canonical uses
Unsafe code without a safety contract, detached tasks, hidden blocking, and startup schema mutation.
### Version/compatibility policy
Pin toolchain and MSRV; upgrade through reviewed lockfile changes.
### Project/package structure
Separate bootstrap, domain, application, transport, and infrastructure modules.
### Ownership/dependency direction
Adapters depend inward on domain contracts and do not own business policy.
### Naming/formatting
Use rustfmt and Clippy-compatible names; document public APIs.
### Typing/type-system policy
Prefer enums, newtypes, validated constructors, and typed errors.
### Error handling
Map errors at boundaries without leaking internals.
### Resource management
Bound pools, queues, bodies, and task lifetimes.
### Concurrency/async/cancellation
Every spawned task has an owner, cancellation path, and bounded work.
### Configuration/secrets
Validate configuration once and never log secrets.
### Logging/observability
Use structured tracing, correlation, latency, and failure fields.
### Dependency policy
Keep features minimal, audit transitive risk, and justify crates.
### Database boundary
Persistence is behind interfaces; Liquibase owns schema evolution.
### Testing
Use deterministic unit, integration, contract, and failure-path tests.
### Security pitfalls
Review authorization, input bounds, deserialization, CORS, and secrets.
### Performance/resource pitfalls
Reject unbounded allocation, blocking work, N+1 queries, and retries.
### Common findings
Detached tasks, ordinary-path unwraps, hidden DB calls, and oversized features.
### Exceptions
Scope, approval, expiry, and migration target are mandatory.
### Review evidence
Report paths, rule IDs, commands, and agent runtime evidence separately.
