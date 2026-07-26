# Liquibase checklist

Check one root, ordered includes, unique immutable changesets, SQL child files,
preconditions, checksum discipline, credentials, validate/status/update-sql,
fresh and upgrade tests, expand–migrate–contract, destructive approvals,
separate migration role, and pre-rollout execution. Flag edited deployed
history, blanket checksum bypass, startup migration, fixtures as history, and
competing frameworks.

## Review procedure and artifacts

### Identity and structure
Record database target, changelog root, ordering, deployment role, and planner identity.
### Dependencies and correctness
Check includes, checksums, preconditions, rollback/expand-migrate-contract behavior, and idempotence.
### Errors, concurrency, and operations
Review lock waits, failed updates, status/validate output, observability, and recovery steps.
### Security, database, and migrations
Verify least-privilege migration credentials and separation from application roles.
### Performance and configuration
Check lock duration, destructive operations, timeouts, and environment configuration.
### Tests, evidence, and classification
Record fresh-install, upgrade, validation, and generated SQL evidence with rule IDs.
### Exceptions
Never use an exception to rewrite deployed history; record owner and expiry.

## Primary sources

[Liquibase changelogs](https://docs.liquibase.com/concepts/changelogs/home.html)
and [changesets](https://docs.liquibase.com/reference-guide/changelog-attributes/what-is-a-changeset).
