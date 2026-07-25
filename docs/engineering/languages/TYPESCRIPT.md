# TypeScript baseline

## Scope

TypeScript is canonical for SvelteKit/browser code, generated clients/contracts,
frontend tests, and tooling. Production Node backends, workers, daemons,
direct DB access, and authoritative domain logic are forbidden by owner policy.

Use strict compiler settings, no implicit `any`, `unknown` then narrowing at
untrusted boundaries, and no blanket `@ts-ignore`, lint disables, or unchecked
casts. Prefer generated API clients and runtime validation for network/storage
data. Keep browser/server modules separate; never ship secrets in public
environment variables. Use safe rendering, abortable requests/timeouts,
dependency and bundle discipline, deterministic tests, accessibility, semantic
HTML, and approved formatting/lint gates.

## Review evidence

Inspect `tsconfig`, generated-code jobs, environment imports, route boundaries,
security headers, contract tests, and browser bundles. Framework migration from
style preference alone is not a defect.

## Primary sources

[TypeScript](https://www.typescriptlang.org/docs/),
[Svelte](https://svelte.dev/docs/svelte), and
[SvelteKit](https://svelte.dev/docs/kit).

## Operational review matrix

### Canonical use cases
SvelteKit routes, browser code, generated clients, and frontend tooling.
### Forbidden/non-canonical uses
Production Node backends, direct database authority, and browser secrets.
### Version/compatibility policy
Pin Node/package-manager versions and review lockfile/compiler changes together.
### Project/package structure
Separate browser, server, routes, generated code, and validation modules.
### Ownership/dependency direction
UI and route adapters consume contracts and do not own persistence policy.
### Naming/formatting
Use strict compiler, formatting, lint, and accessibility settings.
### Typing/type-system policy
Narrow `unknown`, avoid unchecked casts, and synchronize generated types.
### Error handling
Render stable user errors and log only redacted diagnostics server-side.
### Resource management
Abort requests, bound uploads, and prevent unbounded client caches.
### Concurrency/async/cancellation
Every fetch has timeout/abort and SSR work has an explicit lifecycle.
### Configuration/secrets
Only public values reach browser bundles; secrets stay server-side.
### Logging/observability
Use correlation IDs, latency signals, and redaction-aware logs.
### Dependency policy
Prefer audited packages and track client bundle impact.
### Database boundary
Frontend code has no database credentials or schema authority.
### Testing
Use type checks, unit, contract, and browser tests for critical flows.
### Security pitfalls
Review XSS, CSRF, SSR leaks, redirects, supply chain, and secret exposure.
### Performance/resource pitfalls
Reject oversized bundles, waterfalls, hydration waste, and reactive loops.
### Common findings
`any`, `@ts-ignore`, public secrets, server imports, and missing aborts.
### Exceptions
Exceptions require scope and owner approval and never authorize DB authority.
### Review evidence
Report compiler/lint/test commands separately from static review.
