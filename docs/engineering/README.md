# Engineering baseline

This directory is the normative engineering-policy load map. Reviewers load the
detected project profile first, then relevant language, framework, database,
cross-cutting, and checklist documents. `MUST` is mandatory, `SHOULD` is the
default requiring written justification when deviated from, and `MAY` is
optional. An `EXCEPTION` is narrow, owner-approved, time-bounded where
possible, and never silently inferred.

The machine-readable registry in `profiles/engineering/` is authoritative for
rule IDs and profile composition. The external template repository supplies
working scaffolds; this repository supplies policy and validation.

## Loading order

```text
engineering-profile.json → project profile → languages/frameworks/database
→ cross-cutting baselines → review checklist → declared exceptions
```

Missing declarations are reported, not fabricated. Existing projects are not
automatically rewritten merely because their structure differs from a default.

## Primary sources

- [Rust](https://doc.rust-lang.org/), [Tokio](https://tokio.rs/), and
  [Clippy](https://doc.rust-lang.org/clippy/)
- [Go](https://go.dev/doc/), [Gin](https://gin-gonic.com/), and
  [pgx](https://pkg.go.dev/github.com/jackc/pgx)
- [Python](https://docs.python.org/3/), [PEPs](https://peps.python.org/), and
  [pytest](https://docs.pytest.org/)
- [TypeScript](https://www.typescriptlang.org/docs/) and
  [SvelteKit](https://svelte.dev/docs/kit)
- [PostgreSQL](https://www.postgresql.org/docs/) and
  [Liquibase](https://docs.liquibase.com/)
