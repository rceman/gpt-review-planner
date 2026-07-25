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
