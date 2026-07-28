# CI Capability Policy

Remote CI is a capability-dependent gate, not a universal repository requirement.
Repository visibility alone MUST NOT decide whether remote CI is required.
When remote CI is unavailable or intentionally disabled, mandatory local runtime gates remain authoritative.

The four policy modes are `required`, `auto`, `optional`, and `disabled`. `auto` is the default: discover CI read-only, require success when an exact-SHA run exists, and report absence or query unavailability as non-blocking. `optional` behaves similarly but explicitly permits absence. `disabled` performs no network query and returns `not_applicable`. `required` blocks on missing, inaccessible, pending, cancelled, timed-out, failed, or otherwise unsuccessful exact-SHA CI.

Only an exact-SHA run with conclusion `success` is successful. `neutral`, `skipped`, and every other completed non-success conclusion are observed blocking outcomes. If jobs metadata is unavailable, the workflow run's status, conclusion, and exact SHA remain authoritative; job metadata is best effort. An observed failed run is never downgraded to unavailable. The planner never fabricates CI evidence. Owners or repository policy may override defaults. Private, internal, offline, local-only, customer-controlled, and cost-constrained repositories may use `auto` or `disabled`; private visibility does not imply `disabled`.

Local compile, lint, test, scope, command, and evidence gates remain mandatory in every mode. Remote CI evidence and local runtime-gate evidence are separate concepts. CI absence permitted by policy is not a deviation or a blocked state.
