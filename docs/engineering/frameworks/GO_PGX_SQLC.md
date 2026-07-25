# Go pgxpool and sqlc baseline

Configure pgxpool explicitly, acquire/release correctly, pass contexts and
timeouts, and make transaction ownership clear. Version sqlc-generated code,
never edit it, and keep queries organized and reviewable. Avoid N+1 and map
PostgreSQL errors deliberately. GORM, auto-migration, startup DDL, and a
competing migration history are forbidden; Liquibase owns evolution.

## Primary sources

[pgx](https://pkg.go.dev/github.com/jackc/pgx), [sqlc](https://docs.sqlc.dev/),
and [PostgreSQL](https://www.postgresql.org/docs/).
