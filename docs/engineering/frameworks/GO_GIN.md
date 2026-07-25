# Go Gin baseline

Canonical services use `cmd/api/main.go`, `internal/bootstrap/`, `config/`,
`domain/`, `service/`, `transport/http/`, and `repository/postgres/`.
Construct dependencies explicitly and call `gin.New()` with explicit recovery,
logging, request IDs, body limits, timeouts, auth, and CORS middleware. Keep
handlers thin, validation/errors consistent, business logic out of middleware,
and use `http.Server` shutdown. Do not retain request contexts; test handlers
and services independently.

## Primary sources

[Gin](https://gin-gonic.com/), [Go net/http](https://pkg.go.dev/net/http), and
[Go context](https://go.dev/doc/database/cancel-operations).

<a id="gin-middleware-001"></a>

## Operational review matrix

### Scope and canonical use cases
Gin is a thin HTTP adapter with explicit middleware and application delegation.
### Forbidden/non-canonical uses
Do not put domain policy, persistence authority, or hidden global state in handlers.
### Version/compatibility policy
Pin Go and Gin; test middleware ordering and public error compatibility on upgrades.
### Ownership/dependency direction
Routes translate protocols; services and repositories own application/database boundaries.
### Resource, concurrency, and cancellation policy
Propagate context, bound bodies and timeouts, and own every goroutine.
### Security and performance pitfalls
Review auth ordering, CORS, request IDs, panic recovery, and unbounded payloads.
### Testing and review evidence
Use handler and middleware tests plus agent-reported runtime gates.
### Exceptions
Record only narrow owner-approved exceptions.
