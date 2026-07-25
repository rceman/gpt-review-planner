# SvelteKit baseline

Canonical frontend structure is `src/lib/`, `components/`, `features/`, `api/`,
`routes/`, `static/`, and `tests/`. Prefer static deployment when SSR is not
materially required; document SSR requirements. Server routes/actions are thin
BFF/proxy work, never authoritative domain logic or database access. Keep
browser/server modules and secrets separate, prefer generated clients/shared
schemas, minimize hydration and client JavaScript, abort stale requests, and
provide loading/error/empty states. Use safe forms, progressive enhancement,
accessibility, CSP/security headers where supported, component/E2E tests, and
no uncontrolled global stores. SvelteKit does not justify a Node backend.

## Primary sources

[SvelteKit](https://svelte.dev/docs/kit), [routing](https://svelte.dev/docs/kit/routing),
and [environment modules](https://svelte.dev/docs/kit/$env-static-private).

Anchor: `SVELTEKIT-SERVER-001`.
