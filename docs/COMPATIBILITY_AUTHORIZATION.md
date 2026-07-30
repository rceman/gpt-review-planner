# Explicit Authorization Required for Compatibility Work

## Policy

Use the simplest canonical implementation for current requirements.
Backward compatibility, forward compatibility, legacy support, migration
support, transitional behavior, and speculative extensibility are prohibited
unless the user explicitly authorizes them for the current task.

## Greenfield default

A project or subsystem is greenfield unless the user explicitly states that
existing production data, deployed clients, external consumers, persisted
state, released APIs, or older supported versions must remain compatible.

For greenfield work implement one canonical schema, protocol, configuration,
storage layout, and execution path. Remove obsolete approaches and fail clearly
on unsupported input. Experiments, bootstrap commits, unreleased branches,
local test data, abandoned implementations, and prototypes do not create a
compatibility requirement.

## Prohibited without explicit authorization

Do not add compatibility shims or adapters, legacy readers or writers,
dual-read/dual-write behavior, old-schema support, protocol negotiation,
automatic format detection, migration layers or commands, fallbacks,
deprecated aliases, transitional flags, polyfills, silent conversion,
automatic legacy imports, parallel old/new operation, old endpoint or CLI
preservation, wrappers kept only for previous callers, speculative extension
points, placeholder adapter packages, or compatibility TODOs.

Disabled, fail-closed, guarded, experimental, and test-only compatibility still
requires authorization.

## Authorization contract

Authorization must identify:

1. the exact legacy version, schema, protocol, API, data, client, or behavior;
2. why compatibility is required;
3. the direction: backward read, backward write, forward read, migration only,
   temporary dual operation, or permanent compatibility;
4. the removal condition, or confirmation that support is permanent.

General phrases such as “robust”, “handle edge cases”, “support upgrades”,
“production-ready”, or “avoid breaking anything” are not authorization.

## Legacy state discovered during work

Do not create a shim automatically. Leave legacy state unchanged, report it,
explain whether it blocks the task, and request a decision only when the task
cannot continue safely. Otherwise continue with the canonical design and keep
legacy state out of scope.

## Required patch declaration

Without authorization:

```text
Compatibility scope: none
Compatibility authorization: not granted
Canonical implementation: <single schema/protocol/path>
Legacy behavior: unsupported and out of scope
```

With authorization:

```text
Compatibility scope: <exact authorized scope>
Authorization source: <user instruction or approved ADR>
Supported legacy versions: <exact versions>
Compatibility direction: <read/write/migrate/dual-operation>
Removal condition: <date, release, migration completion, or permanent>
```

## Implementation gate

Before producing a patch, remove unauthorized fallback branches, legacy
schemas, adapters, compatibility flags, dual paths, migration utilities,
deprecated aliases, and speculative compatibility abstractions.

## Agent execution gate

The local agent must not introduce compatibility behavior as an integration
fix. Stop and report:

```text
BLOCKED_UNAUTHORIZED_COMPATIBILITY_CHANGE

Required compatibility behavior:
<description>

Reason it appears necessary:
<gate failure or concrete evidence>

User authorization:
not present

Repository changes:
none
```

## Review gate

Reject unauthorized compatibility work even when tests pass or the behavior is
small, defensive, disabled, or unreleased:

```text
Scope violation: unauthorized compatibility complexity
Required correction: remove the compatibility behavior
```

## Evidence requirement

Without authorization evidence contains:

```json
{
  "compatibility_scope": "none",
  "compatibility_authorized": false,
  "compatibility_features_added": [],
  "legacy_paths_added": [],
  "fallbacks_added": [],
  "migration_behavior_added": []
}
```

## Anti-evasion rule

Classify compatibility by behavior, not naming. A guard, bridge, converter,
normalizer, resilience path, import helper, or recovery mechanism that
preserves or interprets behavior outside the canonical implementation is
compatibility work.

## Default decision

Choose one direct canonical implementation unless the user explicitly
authorizes additional compatibility scope.
