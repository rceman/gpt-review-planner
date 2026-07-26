# SvelteKit checklist

Check canonical structure, static-versus-justified SSR, thin server routes,
browser/server modules, generated contracts, public environment variables,
hydration/bundle behavior, aborts, states, forms, accessibility, CSP, and
component/E2E tests. Flag DB clients, authoritative domain logic, leaked
secrets, and an implicit Node service.

## Review procedure and artifacts

### Identity and structure
Record profile, SvelteKit adapter, route/server boundaries, generated clients, and lock.
### Dependencies and correctness
Check strict TypeScript, contract synchronization, form behavior, and SSR assumptions.
### Errors, concurrency, and operations
Review loading/error states, aborts, SSR lifecycle, observability, and deployment health.
### Security, database, and migrations
Verify public env values, XSS/CSRF/CSP, no DB credentials, and backend migration ownership.
### Performance and configuration
Check hydration, bundle, image, cache, request, and configuration budgets.
### Tests, evidence, and classification
Record type, unit, accessibility, component, and browser/E2E evidence with severity.
### Exceptions
Require explicit owner scope and never authorize frontend database authority.

## Primary sources

[SvelteKit](https://svelte.dev/docs/kit) and
[Svelte accessibility](https://svelte.dev/docs/svelte).
