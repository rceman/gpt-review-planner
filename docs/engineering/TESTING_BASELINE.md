# Testing baseline

Use unit, integration, contract, and E2E tests at the boundary that owns the
behavior. Fixtures are deterministic; unit tests do not silently use real
network services. Use real PostgreSQL where transaction/query semantics matter,
with a schema created by Liquibase. Cover failure, timeout, concurrency,
cancellation, security, migration upgrade paths, and graceful shutdown where
applicable. GPT must not claim tests it did not execute; runtime gates belong to
the local coding agent.

Review evidence names exact commands, results, environment, and logs. Avoid
tests that only assert implementation details, sleep-based races, shared mutable
fixtures, or a passing happy path for an unbounded input.

## Primary sources

[pytest](https://docs.pytest.org/), [Go testing](https://go.dev/doc/tutorial/add-a-test),
[Rust testing](https://doc.rust-lang.org/book/ch11-01-writing-tests.html), and
[Liquibase](https://docs.liquibase.com/).

<a id="test-001"></a>
