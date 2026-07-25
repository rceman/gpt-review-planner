# Go baseline

## Scope

Go is the secondary backend profile using Gin, pgxpool, and sqlc. Use module
boundaries, `cmd/` and `internal/`, narrow consumer-defined interfaces, and
explicit dependency construction; no service locator or global mutable state.

## Rules

Propagate `context.Context` as the first request-path argument; never store a
request context. Wrap errors and preserve `errors.Is`/`errors.As`; do not panic
for expected failures or ignore errors without explanation. Own goroutines,
bound workers/queues, channel close rules, cancellation, shutdown, and HTTP/DB
timeouts. Use `gofmt`, `go vet`, approved static analysis, and the race detector
where feasible. Avoid unbounded reads, unsafe subprocesses, and middleware
business logic. Use pgxpool/sqlc and Liquibase-only schema evolution.

## Testing and evidence

Use table tests where useful, deterministic fixtures, handler/service separation,
and cancellation/concurrency tests. Record exact quality-gate commands.

## Primary sources

[Effective Go](https://go.dev/doc/effective_go),
[Go context](https://go.dev/blog/context), [Gin](https://gin-gonic.com/),
[pgx](https://pkg.go.dev/github.com/jackc/pgx), and [sqlc](https://docs.sqlc.dev/).

Anchors: `GO-CONTEXT-001` `GO-ERROR-001`.
