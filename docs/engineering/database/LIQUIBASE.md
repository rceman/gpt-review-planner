# Liquibase baseline

Liquibase is the sole schema authority in canonical projects. Use one root
changelog with explicit ordered includes, globally unique immutable changesets,
and PostgreSQL-specific SQL child files for substantial DDL. YAML orchestrates
metadata; repeatable/run-on-change objects are limited to suitable views and
functions.

Applied changesets MUST NOT be edited; correct forward. Use preconditions for
assumptions and safe failure, never blanket checksum bypass or casual
`validCheckSum`. Credentials stay out of properties. Provide validate, status,
and update-sql/dry-run operations, fresh-database and supported-upgrade tests,
and expand–migrate–contract for breaking changes. Destructive operations are
isolated and approved. Migration runs before application rollout with a
separate role; never at application startup. Fixtures are not schema history.

## Contract tree

```text
db/{README.md,liquibase.properties.example,changelog/{db.changelog-root.yaml,releases/,repeatable/},fixtures/,scripts/{validate.sh,status.sh,update-sql.sh,update.sh}}
```

## Primary sources

[Liquibase changelogs](https://docs.liquibase.com/concepts/changelogs/home.html),
[changesets](https://docs.liquibase.com/reference-guide/changelog-attributes/what-is-a-changeset),
and [PostgreSQL DDL](https://www.postgresql.org/docs/current/ddl.html).

<a id="liquibase-001"></a>
<a id="liquibase-changeset-001"></a>

## Operational review matrix

### Scope and canonical use cases
Liquibase is the one ordered authority for PostgreSQL schema evolution.
### Forbidden/non-canonical uses
Reject startup migrations, competing tools, mutable applied changesets, and ambiguous roots.
### Version/compatibility policy
Pin Liquibase and database compatibility; validate checksums and rollback policy.
### Ownership/dependency direction
Deployment automation applies changesets; services consume the resulting schema.
### Resource, concurrency, and cancellation policy
Use bounded locks/timeouts and make failed changesets observable and recoverable.
### Security and performance pitfalls
Review grants, destructive SQL, lock duration, indexes, and data movement.
### Testing and review evidence
Run validation and representative migration tests through the local agent.
### Exceptions
No exception may silently replace the canonical migration authority.
