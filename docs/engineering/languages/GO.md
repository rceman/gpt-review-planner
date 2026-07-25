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

<a id="go-context-001"></a>
<a id="go-error-001"></a>

## Operational review matrix

### Canonical use cases
Explicit services, workers, and adapters with request-scoped cancellation.
### Forbidden/non-canonical uses
Ignored errors, unbounded goroutines, global mutable service state, and startup DDL.
### Version/compatibility policy
Pin Go and the module graph; review `go.mod` and `go.sum` changes.
### Project/package structure
Keep `cmd`, `internal`, transport, application, and infrastructure ownership visible.
### Ownership/dependency direction
Handlers translate protocols; application code does not depend on Gin or drivers.
### Naming/formatting
Use gofmt, standard names, small interfaces, and public API comments.
### Typing/type-system policy
Prefer concrete types, typed errors, and explicit nil handling.
### Error handling
Wrap with `%w`, classify at boundaries, and return stable public errors.
### Resource management
Close bodies, bound pools/queues, and make goroutine ownership explicit.
### Concurrency/async/cancellation
Propagate `context.Context`; every goroutine has a bounded lifetime.
### Configuration/secrets
Validate once and keep secrets out of logs and metrics.
### Logging/observability
Use structured logs, request IDs, latency, and error classification.
### Dependency policy
Prefer the standard library and justify each module.
### Database boundary
Repositories own persistence; Liquibase owns schema changes.
### Testing
Use deterministic table-driven, integration, and contract tests.
### Security pitfalls
Bound input, authorization, SQL parameters, redirects, and error exposure.
### Performance/resource pitfalls
Reject goroutine leaks, fan-out, missing timeouts, and per-request pools.
### Common findings
Ignored close errors, `context.Background()` in request paths, and global clients.
### Exceptions
Record narrow, approved, expiring exceptions in the declaration.
### Review evidence
Tie findings to paths, rule IDs, commands, and agent results.
