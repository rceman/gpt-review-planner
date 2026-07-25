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
