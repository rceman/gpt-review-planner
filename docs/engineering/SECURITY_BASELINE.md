# Security baseline

MUST enforce least privilege, protect secrets, separate authentication from
authorization, use secure cookies/CSRF controls where applicable, restrictive
CORS, CSP/security headers where supported, body and rate limits, safe path
handling, SSRF/command/SQL-injection defenses, safe deserialization, dependency
audits, and redacted structured logs. Errors expose stable client information,
not credentials, queries, stack traces, or sensitive payloads.

Review subprocess argument arrays and timeouts, archive extraction traversal,
untrusted URLs, browser bundles, migrations and database roles, and production
fallback configuration. A framework default is not evidence of safe application
configuration.

## Primary sources

[OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/),
[PostgreSQL roles](https://www.postgresql.org/docs/current/user-manag.html),
and [Python subprocess](https://docs.python.org/3/library/subprocess.html).

Anchors: `SEC-SECRETS-001` `SEC-INPUT-001`.
