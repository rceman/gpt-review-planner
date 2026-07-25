# Project exceptions

Exceptions are declarations, not informal waivers. Each exception MUST name a
stable rule ID, non-empty reason and scope, owner approver, and optional UTC
expiry. `migration_target` describes future metadata only; it does not
authorize a migration or force a rewrite. Expired or overbroad exceptions fail
validation.

`legacy-python-service` permits maintenance of an existing Python production
backend while retaining security, configuration, typing, testing, resource,
and Liquibase rules. It does not permit new Node backends or automatically
mandate a Rust rewrite.

Reviewers report valid exceptions as documented deviations, invalid exceptions
as contract failures, and absent declarations as missing rather than fabricating
one. The exact pinned catalog remains authoritative.

## Primary sources

[RFC 3339](https://www.rfc-editor.org/rfc/rfc3339) and repository schemas define
serialization constraints; owner approval is the authority for acceptability.

<a id="exception-001"></a>
