# Observability

Services SHOULD emit structured logs, correlation/request IDs, traces and
actionable metrics, plus health/readiness signals and graceful-shutdown events.
Events are stable enough for operations; logs never contain secrets or
unbounded request payloads. Health checks distinguish process liveness from
dependency readiness and do not become an unbounded database load.

Review evidence includes instrumentation boundaries, propagation tests,
redaction tests, dashboards/alerts where operationally required, and shutdown
behavior. Do not add noisy logging or metrics without an operational question.

## Primary sources

[OpenTelemetry](https://opentelemetry.io/docs/),
[Go slog](https://go.dev/blog/slog), and
[Rust tracing](https://docs.rs/tracing/).

<a id="obs-001"></a>
