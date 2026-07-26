# Go pgxpool and sqlc baseline

Configure pgxpool explicitly, acquire/release correctly, pass contexts and
timeouts, and make transaction ownership clear. Version sqlc-generated code,
never edit it, and keep queries organized and reviewable. Avoid N+1 and map
PostgreSQL errors deliberately. GORM, auto-migration, startup DDL, and a
competing migration history are forbidden; Liquibase owns evolution.

## Primary sources

[pgx](https://pkg.go.dev/github.com/jackc/pgx), [sqlc](https://docs.sqlc.dev/),
and [PostgreSQL](https://www.postgresql.org/docs/).

<a id="pgx-pool-001"></a>
<a id="sqlc-generated-001"></a>

## Operational review matrix

### Scope and canonical use cases
pgx and sqlc provide the explicit PostgreSQL repository boundary.
### Forbidden/non-canonical uses
Do not hand-edit generated code, create per-request pools, or run startup DDL.
### Version/compatibility policy
Pin toolchain and generator versions; review generated diffs and query fixtures.
### Ownership/dependency direction
Generated queries stay in infrastructure and are consumed through application interfaces.
### Resource, concurrency, and cancellation policy
Bound pgx pools, propagate context, and set query/transaction timeouts.
### Security and performance pitfalls
Use parameters, least privilege, bounded result sets, and inspect query plans.
### Testing and review evidence
Regenerate deterministically and report generated-source plus integration evidence.
### Exceptions
Exceptions require scope, owner, expiry, and migration details.
