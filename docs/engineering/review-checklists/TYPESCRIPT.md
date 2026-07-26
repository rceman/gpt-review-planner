# TypeScript checklist

Check strict config, `unknown` narrowing, generated clients, runtime boundary
validation, browser/server separation, secrets, safe rendering, abortable
requests, bundle size, accessibility, and deterministic tests. Flag implicit
any, blanket suppressions, unchecked casts, direct DB access, Node backends,
and duplicated contract authority.

## Review procedure and artifacts

### Identity and structure
Record TypeScript config, package manager lock, browser/server module map, and planner lock.
### Dependencies and correctness
Check generated clients, runtime validation, strictness, contract compatibility, and semantic HTML.
### Errors, concurrency, and operations
Review stable UI errors, abortable requests, SSR lifecycle, telemetry, and error redaction.
### Security, database, and migrations
Verify XSS/CSRF/SSR leaks, public environment values, no DB access, and backend migration ownership.
### Performance and configuration
Check bundle/hydration budgets, cache behavior, timeouts, and validated configuration.
### Tests, evidence, and classification
Record typecheck, lint, unit, contract, accessibility, and browser results with rule IDs.
### Exceptions
Require owner approval, narrow scope, expiry, and evidence; suppressions are not defaults.

## Primary sources

[TypeScript](https://www.typescriptlang.org/docs/) and
[SvelteKit](https://svelte.dev/docs/kit).
