# Rust SQLx baseline

Use PostgreSQL, explicit pool limits/timeouts, repositories for the SQL
boundary, and explicit transaction ownership. Keep SQL reviewable, avoid N+1,
map database errors deliberately, and enable only required UUID/time/decimal
features. Compile-time/offline checking and versioned `.sqlx/` metadata are
used when the workflow supports them; generated metadata is never hand-edited.
SQLx migrations, startup DDL, and competing schema history are forbidden;
Liquibase owns evolution.

## Primary sources

[SQLx](https://docs.rs/sqlx/) and [PostgreSQL](https://www.postgresql.org/docs/).

<a id="sqlx-pool-001"></a>

## Operational review matrix

### Scope and canonical use cases
SQLx is the typed PostgreSQL adapter behind application repositories.
### Forbidden/non-canonical uses
Do not hide queries in handlers, mutate schema at startup, or use unbounded pools.
### Version/compatibility policy
Pin SQLx features and offline metadata; review migrations and generated query evidence together.
### Ownership/dependency direction
Repositories own persistence mechanics while domain code remains database-agnostic.
### Resource, concurrency, and cancellation policy
Bound pool connections, transaction lifetimes, query timeouts, and cancellation.
### Security and performance pitfalls
Use parameters, least privilege, bounded queries, and review N+1 behavior.
### Testing and review evidence
Keep `.sqlx`/query evidence current and report deterministic integration coverage.
### Exceptions
Use only approved, scoped, expiring project exceptions.
