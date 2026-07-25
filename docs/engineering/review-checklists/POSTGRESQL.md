# PostgreSQL checklist

Check roles/least privilege, pool budgets, timeouts, transaction/isolation
behavior, constraints/FKs, measured indexes, N+1, UTC/time and money types,
payload bounds/pagination, locks, backups, schema observability, and Liquibase
test creation. Flag app-role DDL, startup DDL, speculative indexes, manual
drift, and competing migration histories.

## Primary sources

[PostgreSQL](https://www.postgresql.org/docs/current/) and
[EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html).
