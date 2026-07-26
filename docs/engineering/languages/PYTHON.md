# Python baseline

## Scope

Python is allowed for scripts, automation, tooling, generation, conversion,
tests, references, prototypes, and AI/ML work. New production services require
an exception; this policy selects no canonical Python web framework. The
legacy-python-service profile permits maintenance without automatic rewrite.

## Rules

Prefer `pyproject.toml`, `src/` for reusable packages, explicit supported Python
versions, lockfiles, and separate runtime/test/dev dependencies. Use Ruff and
Pyright plus pytest. Public boundaries require annotations; `Any` is confined
to dynamic boundaries. Use specific exceptions, preserve chains with
`raise ... from ...`, return non-zero CLI exits, `pathlib.Path`, explicit
encodings, context managers, safe temporary files, atomic replacement, and
streaming for unbounded input. Subprocesses use argument arrays, `check=True`,
timeouts, and no `shell=True` without a documented need. Async work is bounded,
cancellable, and not blocked by synchronous work. Config is centralized and
secrets never enter logs or command-line arguments. Use timezone-aware datetimes,
fixed-point money, safe deserialization, and archive/path traversal defenses.
Liquibase remains schema authority.

## Primary sources

[Python](https://docs.python.org/3/), [PEPs](https://peps.python.org/),
[packaging](https://packaging.python.org/), [pytest](https://docs.pytest.org/),
[Ruff](https://docs.astral.sh/ruff/), [Pyright](https://microsoft.github.io/pyright/),
and [subprocess](https://docs.python.org/3/library/subprocess.html).

<a id="py-subprocess-001"></a>
<a id="py-typing-001"></a>

## Operational review matrix

### Canonical use cases
Bounded tools, tests, prototypes, and explicitly approved legacy services.
### Forbidden/non-canonical uses
New production Python backends require an approved legacy exception.
### Version/compatibility policy
Pin interpreter and lockfile; document supported versions and targets.
### Project/package structure
Separate CLI, domain, adapters, configuration, and tests.
### Ownership/dependency direction
Shell/HTTP/database adapters remain at boundaries with explicit interfaces.
### Naming/formatting
Use repository formatter, lint policy, and import ordering.
### Typing/type-system policy
Type stable boundaries and narrow `Any` immediately after validation.
### Error handling
Catch specific exceptions, preserve causes, and return stable errors.
### Resource management
Use context managers, bounded subprocesses, timeouts, and cleanup.
### Concurrency/async/cancellation
Use structured task ownership; do not hide event-loop blocking work.
### Configuration/secrets
Centralize validated settings and keep environment values out of logs.
### Logging/observability
Emit structured, redacted events with correlation and failure context.
### Dependency policy
Lock, audit, and justify runtime dependencies.
### Database boundary
Approved services use repository boundaries and Liquibase, not startup DDL.
### Testing
Prefer deterministic pytest/unittest tests and boundary coverage.
### Security pitfalls
Review subprocess arguments, deserialization, traversal, credentials, and temp files.
### Performance/resource pitfalls
Reject unbounded reads, output, retries, worker pools, and fixture growth.
### Common findings
Shell strings, broad catches, globals, and untyped public functions.
### Exceptions
Legacy exceptions include target, scope, owner, and expiry.
### Review evidence
Separate static findings from local-agent runtime evidence.
