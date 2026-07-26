# Python test-suite profile

Use pytest with deterministic fixtures, isolated resources, explicit supported
Python versions, and no accidental real network. Apply Python typing, error,
subprocess, security, and dependency rules. PostgreSQL semantics use a
Liquibase-created test schema when relevant. This profile does not authorize a
production backend.

## Primary sources

[pytest](https://docs.pytest.org/) and [Python](https://docs.python.org/3/).

## Profile contract

### Capabilities and rules
Capabilities are isolated fixtures, deterministic tests, and tests. Required rules cover Python typing/subprocess, API bounds, configuration, security, performance, testing, template, and exceptions.
### Loaded documents and structure
Load Python, testing, dependency, security, and configuration documents. Keep fixtures isolated from real networks, credentials, and production databases.
### Template requirements
Require `pyproject.toml`, `tests`, and `engineering-profile.json`; Liquibase-created test schemas are allowed only when declared.
### Security, resources, testing, and operations
Review fixture cleanup, fake clocks, network blocking, subprocess timeouts, coverage intent, and reproducible agent-executed gates.
### Non-goals and exceptions
This profile does not authorize a production backend or unbounded integration environment.
### Review procedure and artifacts
Validate the lock/declaration, classify tests by boundary, and return fixture inventory, commands, outcomes, and exceptions.
