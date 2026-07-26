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

<a id="sveltekit-server-001"></a>
<a id="sveltekit-ssr-001"></a>

## Operational review matrix

### Scope and canonical use cases
SvelteKit owns presentation, routing, SSR coordination, and generated client use.
### Forbidden/non-canonical uses
Routes must not own domain policy, database credentials, or schema authority.
### Version/compatibility policy
Pin SvelteKit/TypeScript versions and review SSR, adapter, and generated-client changes.
### Ownership/dependency direction
Server routes call backend contracts; browser modules cannot import server secrets.
### Resource, concurrency, and cancellation policy
Abort fetches, bound uploads, and keep SSR work scoped to the request lifecycle.
### Security and performance pitfalls
Review SSR data leaks, CSRF/XSS, hydration cost, bundle size, and open redirects.
### Testing and review evidence
Run type, contract, accessibility, and browser gates through the local agent.
### Exceptions
Document only scoped, approved exceptions.
