# Performance baseline

Measure representative load before claiming an optimization. Record idle and
peak RAM, CPU, cold start, latency percentiles, binary/deployment size,
browser JavaScript transfer/execution, dependency count, and bootstrap/build
duration when relevant. Bound queues, request bodies, rows, messages, worker
counts, retries, and timeouts; apply backpressure rather than unbounded work.

Review allocation/cloning, N+1 database access, pagination, cache lifetime,
browser hydration, and blocking work on async executors. A smaller or faster
alternative is not presumed correct without evidence. Tests cover cancellation,
concurrency, overload, and timeout behavior where those affect the contract.

## Primary sources

[Tokio guidance](https://tokio.rs/tokio/tutorial),
[PostgreSQL EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html),
and [SvelteKit performance](https://svelte.dev/docs/kit/performance).

Anchor: `PERF-BOUNDS-001`.
