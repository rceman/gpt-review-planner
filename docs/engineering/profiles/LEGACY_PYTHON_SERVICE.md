# Legacy Python service profile

This profile permits maintenance of an existing deployed Python backend under a
declared owner exception. It retains security, configuration, typing, testing,
resource, observability, and Liquibase rules, does not authorize Node backends,
and does not mandate an automatic Rust rewrite. A migration target is metadata;
the owner decides whether and when to migrate.

## Primary sources

[Python](https://docs.python.org/3/), [PEPs](https://peps.python.org/), and
[Liquibase](https://docs.liquibase.com/).

## Profile contract

### Capabilities and rules
Capabilities are approved Python backend, PostgreSQL, Liquibase, shutdown, observability, tests, and safe configuration. Required rules include the Python exception, typing, subprocess, database, security, configuration, bounds, testing, and template rules.
### Loaded documents and structure
Load Python, PostgreSQL, Liquibase, security, configuration, dependency, testing, and exception documents. Preserve existing service boundaries while isolating migration work.
### Template requirements
Require `engineering-profile.json` and a declared legacy exception; do not add Node backends or startup migrations.
### Security, resources, testing, and operations
Review subprocess bounds, secret redaction, input validation, pool/resource limits, observability, deterministic tests, and migration CI evidence.
### Non-goals and exceptions
Legacy status is not authorization for new Python services or automatic Rust rewrites. Every exception has owner, scope, target, and expiry.
### Review procedure and artifacts
Validate the pinned lock, declaration, exception applicability, and migration metadata; report static findings separately from agent runtime evidence.
