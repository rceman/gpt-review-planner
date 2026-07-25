# Liquibase checklist

Check one root, ordered includes, unique immutable changesets, SQL child files,
preconditions, checksum discipline, credentials, validate/status/update-sql,
fresh and upgrade tests, expand–migrate–contract, destructive approvals,
separate migration role, and pre-rollout execution. Flag edited deployed
history, blanket checksum bypass, startup migration, fixtures as history, and
competing frameworks.

## Primary sources

[Liquibase changelogs](https://docs.liquibase.com/concepts/changelogs/home.html)
and [changesets](https://docs.liquibase.com/reference-guide/changelog-attributes/what-is-a-changeset).
