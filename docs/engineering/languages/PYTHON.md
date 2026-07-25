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

Anchors: `PY-SUBPROCESS-001` `PY-TYPING-001`.
