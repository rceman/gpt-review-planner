# Go checklist

Check module boundaries, `cmd/internal`, Gin middleware, context propagation,
error wrapping, goroutine ownership, worker bounds, timeouts, shutdown,
gofmt/vet/race gates, pgx/sqlc, secrets, and table tests. Flag panics for
expected failures, stored request contexts, ignored errors, global state, and
unbounded reads.

## Primary sources

[Go](https://go.dev/doc/), [context](https://go.dev/blog/context), and
[Gin](https://gin-gonic.com/).
