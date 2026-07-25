# Legacy Python service profile

This profile permits maintenance of an existing deployed Python backend under a
declared owner exception. It retains security, configuration, typing, testing,
resource, observability, and Liquibase rules, does not authorize Node backends,
and does not mandate an automatic Rust rewrite. A migration target is metadata;
the owner decides whether and when to migrate.

## Primary sources

[Python](https://docs.python.org/3/), [PEPs](https://peps.python.org/), and
[Liquibase](https://docs.liquibase.com/).
