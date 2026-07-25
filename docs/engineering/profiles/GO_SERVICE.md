# Go service profile

Use `cmd/`, `internal/`, explicit bootstrap/config/domain/service/transport and
repository boundaries. Gin is canonical for HTTP; pgxpool/sqlc and Liquibase
are canonical for PostgreSQL. Apply Go context, error, goroutine, timeout,
security, observability, and testing rules. A plain `net/http` service requires
a documented exception.

## Primary sources

[Go](https://go.dev/doc/), [Gin](https://gin-gonic.com/), and
[pgx](https://pkg.go.dev/github.com/jackc/pgx).
