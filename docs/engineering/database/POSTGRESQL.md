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

<a id="db-role-001"></a>
<a id="postgres-pool-001"></a>

## Operational review matrix

### Scope and canonical use cases
PostgreSQL is the canonical relational store for approved backend profiles.
### Forbidden/non-canonical uses
Application startup must not compete with Liquibase or grant ordinary roles DDL authority.
### Version/compatibility policy
Pin server/client compatibility and review extension, index, and pool changes.
### Ownership/dependency direction
Liquibase owns schema evolution; application repositories own runtime queries.
### Resource, concurrency, and cancellation policy
Budget connections across replicas, set statement timeouts, and cancel abandoned work.
### Security and performance pitfalls
Use least privilege, parameterized queries, bounded result sets, and reviewed indexes.
### Testing and review evidence
Record migration, query, backup/restore, and integration evidence from the local agent.
### Exceptions
DDL ownership exceptions require explicit scope and expiry.
