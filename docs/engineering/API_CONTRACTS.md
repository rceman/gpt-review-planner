# API contracts

Each externally consumed API MUST have an explicit authority such as
OpenAPI/JSON Schema/Protobuf or an approved equivalent. Prefer generated
TypeScript clients and protocol types; do not duplicate DTOs manually across
frontend and backend. Define stable errors, pagination, idempotency,
timeouts, compatibility/deprecation, authentication boundaries, and contract
tests. Runtime validation remains necessary at untrusted network and storage
boundaries even with static types.

SvelteKit is a presentation/BFF boundary, not authoritative domain logic or a
database boundary. Review generated-code provenance and CI regeneration checks.

## Primary sources

[OpenAPI](https://spec.openapis.org/oas/latest.html),
[JSON Schema](https://json-schema.org/specification), and
[TypeScript](https://www.typescriptlang.org/docs/).

<a id="api-timeout-001"></a>
