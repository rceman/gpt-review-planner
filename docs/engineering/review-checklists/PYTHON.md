# Python checklist

Check pyproject/layout/version locks, Ruff/Pyright/pytest, annotations and
`Any`, exception chains, CLI exits, pathlib/encoding/context managers,
subprocess arrays/check/timeouts, async cancellation, config/secrets, timezone
and money types, deserialization, archive traversal, and isolated fixtures.
Legacy profile does not mandate rewrite.

## Review procedure and artifacts

### Identity and structure
Record profile, interpreter/lock versions, package layout, CLI boundaries, and planner lock.
### Dependencies and correctness
Check dependency justification, typing, serialization, return codes, and domain invariants.
### Errors, concurrency, and operations
Review exception chains, async cancellation, subprocess ownership, cleanup, and observability.
### Security, database, and migrations
Verify secrets, traversal, untrusted input, least privilege, and declared Liquibase behavior.
### Performance and configuration
Check output/input bounds, timeouts, retries, configuration validation, and fixture resource budgets.
### Tests, evidence, and classification
Record unittest/pytest, fixture isolation, coverage intent, and agent runtime results.
### Exceptions
Legacy exceptions need owner, scope, migration target, expiry, and evidence.

## Primary sources

[Python](https://docs.python.org/3/), [pytest](https://docs.pytest.org/), and
[Ruff](https://docs.astral.sh/ruff/).
