# Template repository contract

Every external starter template MUST pin an immutable planner commit in
`.gpt-workflow.lock`, include exactly one valid engineering profile, and expose
no unapproved exceptions. It MUST implement selected required paths and
capabilities and omit forbidden technologies.

Templates MUST include applicable bootstrap, quality gates, tests,
PostgreSQL/Liquibase setup, health/readiness, structured observability, and
graceful shutdown. CI validates generated output, not only template source, and
reports planner/profile identity. Normative documents are linked, not copied.
Pins change only through an explicit controlled update.

Future categories are fullstack Rust/SvelteKit, fullstack Go/SvelteKit, Rust
service, Go service, SvelteKit frontend, and Python tools/tests/prototypes; no
legacy Python scaffold is required.

## Evidence and exceptions

Conformance checks record profile, planner lock, generated paths,
forbidden-capability scans, quality-gate results, and exceptions. A template
exception is narrow and owner-approved; it cannot weaken unrelated rules.

## Primary sources

[Cargo](https://doc.rust-lang.org/cargo/), [Go](https://go.dev/doc/),
[SvelteKit](https://svelte.dev/docs/kit), and
[Liquibase](https://docs.liquibase.com/).

<a id="template-001"></a>
