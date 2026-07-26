# Python prototype profile

Prototypes may use Python dependencies and simpler structure while they remain
non-production. Keep secrets/configuration safe, bound resources, preserve
typing at stable boundaries, and document the path to production. A prototype
does not silently become a production service or schema authority.

## Primary sources

[Python](https://docs.python.org/3/) and
[Python packaging](https://packaging.python.org/en/latest/).

## Profile contract

### Capabilities and rules
Capabilities are safe configuration and tests. Required rules cover typing, subprocess, API bounds, security, configuration, performance, testing, template, and exception handling; no backend or database capabilities are declared.
### Loaded documents and structure
Load Python, configuration, security, dependency, testing, and exception documents. Keep prototype code disposable and boundaries explicit.
### Template requirements
Require `README.md` and `engineering-profile.json`; forbid service/database paths and credentials.
### Security, resources, testing, and operations
Use fake external services, bounded files/subprocesses, deterministic fixtures, and evidence of supported interpreter/dependency versions.
### Non-goals and exceptions
Prototype status does not authorize production deployment, schema authority, or silent promotion.
### Review procedure and artifacts
Validate declaration and applicable rules, identify promotion risks, and return findings, test evidence, and a productionization checklist.
