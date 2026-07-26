# Python tool profile

Python is used for bounded scripts, automation, conversion, generation, or
repository tooling. Prefer pyproject, explicit dependencies, pathlib,
timeouts, typed config, Ruff/Pyright, deterministic tests, and safe subprocess
and file handling. This profile does not authorize a production web service.

## Primary sources

[Python](https://docs.python.org/3/) and
[packaging](https://packaging.python.org/en/latest/).

## Profile contract

### Capabilities and rules
Capabilities are safe configuration, deterministic tests, and tests. Required rules cover typed Python boundaries, bounded subprocesses, configuration, security, performance, API timeouts, testing, template, and exceptions.
### Loaded documents and structure
Load Python, configuration, dependency, security, testing, and structure documents. Keep CLI/tool entry points separate from reusable logic.
### Template requirements
Require `pyproject.toml`, `tests`, and `engineering-profile.json`; do not add a production web backend.
### Security, resources, testing, and operations
Review pathlib use, argument arrays, timeouts, output bounds, secret redaction, deterministic tests, and CI logs.
### Non-goals and exceptions
Tooling status does not authorize database authority, network trust, or automatic legacy rewrites.
### Review procedure and artifacts
Validate declaration and capabilities, inspect inputs/outputs, and report reproducible commands and evidence.
