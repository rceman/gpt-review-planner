# Configuration and secrets

Configuration MUST be typed, centralized, validated at startup, and separated
by environment. Provide `.env.example` without secrets; do not scatter raw
environment reads, use insecure production fallbacks, commit credentials, or
place secrets in browser-exposed variables and command-line arguments. Redact
values in logs and errors and test invalid/missing configuration paths.

Evidence includes configuration schema/loaders, deployment manifests, secret
references, startup validation, and redaction tests. A legacy service may retain
its loader under an exception but not its credentials or unsafe defaults.

## Primary sources

[Twelve-Factor config](https://12factor.net/config),
[SvelteKit environment modules](https://svelte.dev/docs/kit/$env-static-private),
and [PostgreSQL client environment](https://www.postgresql.org/docs/current/libpq-envars.html).

Anchor: `CONFIG-001`.
