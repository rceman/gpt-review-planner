# PostgreSQL checklist

Check roles/least privilege, pool budgets, timeouts, transaction/isolation
behavior, constraints/FKs, measured indexes, N+1, UTC/time and money types,
payload bounds/pagination, locks, backups, schema observability, and Liquibase
test creation. Flag app-role DDL, startup DDL, speculative indexes, manual
drift, and competing migration histories.

## Review procedure and artifacts

### Identity and structure
Record schema, roles, pool topology, migration authority, and planner identity.
### Dependencies and correctness
Check constraints, keys, transactions, isolation, time/money types, and query contracts.
### Errors, concurrency, and operations
Review locks, cancellation, statement timeouts, backups, restore evidence, and schema observability.
### Security, database, and migrations
Verify least privilege, no app-role DDL, parameterization, and Liquibase ownership.
### Performance and configuration
Check measured indexes, EXPLAIN plans, pool budgets, pagination, and environment settings.
### Tests, evidence, and classification
Record migration, query, integration, backup/restore, and load evidence with severity classification.
### Exceptions
Require explicit owner scope and expiry for role, schema, or migration deviations.

## Primary sources

[PostgreSQL](https://www.postgresql.org/docs/current/) and
[EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html).
