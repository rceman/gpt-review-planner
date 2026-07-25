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
