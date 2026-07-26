# Project structure

Canonical trees are defaults and review boundaries, not permission to perform
unmeasured reorganizations.

## Full stack

```text
project/{apps/web,services/api,db,contracts,docs/{architecture,adr,operations,security},scripts,tests/{integration,e2e},engineering-profile.json,.gpt-workflow.lock,AGENTS.md}
```

Rust and Go services occupy `services/api`; the frontend occupies `apps/web`.
Service-only projects use `cmd/` or `src/`, a clear domain and transport split,
`db/` when PostgreSQL is used, and tests beside the relevant boundary. Python
reusable packages use `pyproject.toml`, `src/<package>/`, `tests/`, `scripts/`,
and a declaration; genuinely small scripts MAY remain simple.

## Review evidence

Check ownership boundaries, dependency direction, generated-code locations,
configuration paths, test placement, and operational scripts. A deviation is a
finding only when it creates correctness, security, resource, or maintenance
risk or violates an applicable declared rule.

## Primary sources

[Cargo workspaces](https://doc.rust-lang.org/cargo/reference/workspaces.html),
[Go modules](https://go.dev/ref/mod), and
[Python packaging](https://packaging.python.org/en/latest/).

<a id="structure-001"></a>
