# Go service profile

Use `cmd/`, `internal/`, explicit bootstrap/config/domain/service/transport and
repository boundaries. Gin is canonical for HTTP; pgxpool/sqlc and Liquibase
are canonical for PostgreSQL. Apply Go context, error, goroutine, timeout,
security, observability, and testing rules. A plain `net/http` service requires
a documented exception.

## Primary sources

[Go](https://go.dev/doc/), [Gin](https://gin-gonic.com/), and
[pgx](https://pkg.go.dev/github.com/jackc/pgx).

## Profile contract

### Capabilities and rules
Capabilities are Go backend, generated contracts, PostgreSQL, Liquibase, shutdown, observability, and tests. Required rules cover Go context, Gin, pgxpool/sqlc, database, security, configuration, testing, and template contracts; Go error handling is recommended.
### Loaded documents and structure
Load Go, Gin, pgx/sqlc, PostgreSQL, Liquibase, API, security, testing, and structure documents. Keep `cmd`, `internal`, transport, application, and repositories separate.
### Template requirements
Require `cmd`, `internal`, and `engineering-profile.json`; do not introduce a frontend or competing migration path.
### Security, resources, testing, and operations
Inspect context cancellation, middleware, pool/queue bounds, least privilege, timeouts, shutdown, observability, table tests, race/vet output, and CI evidence.
### Non-goals and exceptions
Plain `net/http`, alternate persistence, or legacy deviations require explicit exceptions; no automatic rewrite is implied.
### Review procedure and artifacts
Validate lock/declaration, derive capability rules, inspect ownership, and report rule IDs, paths, commands, and artifacts.
