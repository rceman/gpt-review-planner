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
