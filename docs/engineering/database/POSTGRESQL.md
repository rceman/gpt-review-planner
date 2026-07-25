# PostgreSQL baseline

PostgreSQL is the canonical relational database. Projects MUST define
environment ownership, separate migration and application roles, least
privilege, pool budgets across replicas, and relevant statement/lock/idle-
transaction timeouts. Application roles normally lack DDL.

Use short explicit transactions, choose isolation for behavior, and enforce
invariants with constraints and intentional foreign keys. Indexes require
measured access-pattern evidence; avoid speculative proliferation and N+1
queries. Use `timestamptz`/UTC for absolute time, decimal/fixed-point for money,
bounded payloads and pagination, and justify JSONB. Verify backup/restore and
observe schema version. Test databases come from Liquibase history; no manual
schema dump or competing migration authority.

Review locking, deadlock/retry behavior, transaction ownership, query plans,
role grants, secret handling, and rollout compatibility. UUID versus integer
IDs is a documented project choice, not a universal rule.

## Primary sources

[PostgreSQL roles](https://www.postgresql.org/docs/current/user-manag.html),
[transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html),
[EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html), and
[data types](https://www.postgresql.org/docs/current/datatype.html).

Anchor: `DB-ROLE-001`.
