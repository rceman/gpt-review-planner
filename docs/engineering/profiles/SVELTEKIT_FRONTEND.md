# SvelteKit frontend profile

Use `src/lib`, components/features/api, routes, static, and tests. Prefer
static deployment, justify SSR, use generated contracts, and keep all database
and authoritative domain work behind Rust or Go services. Apply TypeScript,
SvelteKit, API, security, accessibility, performance, and testing rules.

## Primary sources

[SvelteKit](https://svelte.dev/docs/kit) and
[TypeScript](https://www.typescriptlang.org/docs/).

## Profile contract

### Capabilities and rules
Capabilities are frontend, generated contracts, accessibility, and tests. Required rules cover frontend boundaries, TypeScript, API timeouts, security, configuration, performance, testing, template, and exceptions; SSR is recommended.
### Loaded documents and structure
Load TypeScript, SvelteKit, API, security, configuration, performance, testing, and template documents. Use `src/lib`, routes, static assets, and tests.
### Template requirements
Require `src`, `static`, and `engineering-profile.json`; forbid database paths and backend capabilities.
### Security, resources, testing, and operations
Review browser/server separation, public env values, SSR justification, bundle/hydration budgets, accessibility, aborts, component/E2E tests, and CI evidence.
### Non-goals and exceptions
Frontend status never authorizes database credentials, domain authority, or a Node backend.
### Review procedure and artifacts
Validate declaration, inspect generated contracts and route boundaries, and return findings, screenshots/logs where relevant, and test evidence.
