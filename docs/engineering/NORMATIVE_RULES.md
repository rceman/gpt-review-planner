# Normative rules

Rule IDs are stable API. A semantic replacement gets a new ID and deprecation
metadata; an ID is never silently repurposed. Evidence for a rule is the
relevant source path, configuration, test, generated artifact, or explicit
owner exception.

## Stack decisions

- `STACK-FRONTEND-001` MUST use TypeScript + SvelteKit for the canonical
  frontend; static deployment is preferred when SSR is not required.
- `STACK-BACKEND-001` MUST prefer Rust + Tokio + Axum + Tower + SQLx for new
  authoritative services and domain logic.
- `STACK-BACKEND-002` MAY use Go + Gin + pgxpool + sqlc when the Go profile is
  selected or a documented simplicity/team exception applies.
- `STACK-NODE-001` MUST NOT add a production Node.js/TypeScript backend,
  worker, daemon, direct frontend DB client, or migration authority.
- `STACK-PYTHON-001` MUST declare an exception for a new production Python
  service; tools, tests, automation, prototypes, and data work remain allowed.
- `DB-POSTGRES-001` MUST use PostgreSQL in canonical database profiles.
- `DB-LIQUIBASE-001` MUST keep schema evolution in one Liquibase history.
- `DB-MIGRATION-001` MUST NOT use startup DDL or competing migration histories.
- `TS-BOUNDARY-001` MUST keep browser/frontend code away from PostgreSQL and
  authoritative domain logic.
- `CONTRACT-001` SHOULD use generated API clients and protocol types rather
  than duplicated DTO contracts.

## Evidence and exceptions

Reviewers classify a deviation as policy violation only when the rule applies
and no valid exception covers its scope. A style preference is not a defect.
Exceptions state rule, reason, scope, approver, migration metadata, and expiry.

## Primary sources

See the official-source links in [the engineering load map](README.md), and
the individual language/framework/database documents. Owner policy above is
distinct from claims derived from those sources.

<a id="stack-frontend-001"></a>
<a id="stack-backend-001"></a>
<a id="stack-backend-002"></a>
<a id="stack-node-001"></a>
<a id="stack-python-001"></a>
<a id="db-postgres-001"></a>
<a id="db-liquibase-001"></a>
<a id="db-migration-001"></a>
<a id="ts-boundary-001"></a>
<a id="contract-001"></a>
