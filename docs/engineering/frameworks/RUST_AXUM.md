# Rust Axum baseline

Handlers are transport adapters, not domain services. Use explicit cheap-to-clone
application state, domain/module router composition, explicit Tower middleware,
request body limits, timeouts, restrictive CORS, tracing/request IDs,
authn/authz boundaries, stable error responses without internal leakage, and
graceful shutdown. Blocking work uses an appropriate boundary; extractors do
not hide unbounded work. Minimize crate features. Test handlers without full
production bootstrap and keep contracts/generated clients synchronized.

## Primary sources

[Axum](https://docs.rs/axum/), [Tower](https://docs.rs/tower/), and
[Tower HTTP](https://docs.rs/tower-http/).

<a id="axum-boundary-001"></a>

## Operational review matrix

### Scope and canonical use cases
Axum is a transport adapter for bounded HTTP services; handlers delegate to application use cases.
### Forbidden/non-canonical uses
Handlers must not own domain policy, persistence, unbounded blocking, or secret-bearing diagnostics.
### Version/compatibility policy
Pin Rust, Axum, Tower, and feature sets; review upgrades with compatibility tests.
### Ownership/dependency direction
Router, middleware, extractors, application, and infrastructure boundaries remain explicit.
### Resource, concurrency, and cancellation policy
Bound bodies/timeouts and attach shutdown/cancellation to every spawned operation.
### Security and performance pitfalls
Review CORS, auth, request IDs, error leakage, oversized payloads, and blocking work.
### Testing and review evidence
Test handlers at the boundary and report paths, rule IDs, and agent-executed commands.
### Exceptions
Record scoped owner-approved exceptions in the project declaration.
