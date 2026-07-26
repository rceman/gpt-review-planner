# Go checklist

Check module boundaries, `cmd/internal`, Gin middleware, context propagation,
error wrapping, goroutine ownership, worker bounds, timeouts, shutdown,
gofmt/vet/race gates, pgx/sqlc, secrets, and table tests. Flag panics for
expected failures, stored request contexts, ignored errors, global state, and
unbounded reads.

## Review procedure and artifacts

### Identity and structure
Record profile/lock, module boundaries, handlers, services, repositories, and generated sources.
### Dependencies and correctness
Check module justification, contract behavior, error identity, and context propagation.
### Errors, concurrency, and operations
Review wrapping, goroutine ownership, cancellation, shutdown, health, and observability.
### Security, database, and migrations
Verify auth, secrets, parameterized SQL, least privilege, pool budgets, and Liquibase evidence.
### Performance and configuration
Check timeouts, worker bounds, pagination, config validation, and race/vet evidence.
### Tests, evidence, and classification
Record deterministic unit, integration, race, and contract commands with rule classifications.
### Exceptions
Require scoped owner approval, migration metadata, expiry, and artifact location.

## Primary sources

[Go](https://go.dev/doc/), [context](https://go.dev/blog/context), and
[Gin](https://gin-gonic.com/).
