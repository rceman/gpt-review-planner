# Structured Format Policy

## JSON

JSON is the canonical machine-readable format for `manifest.json`, `evidence.json`, validator results, schemas, machine result data, and gateway-owned task and result envelopes. Strict decoding rejects duplicate keys, trailing data, unknown fields where schemas close the object, and ambiguous scalar coercion. Canonical JSON provides matching Go/Python semantics, predictable types, deterministic normalization and hashing, and avoids YAML implicit booleans, dates, and nulls.

## YAML

YAML is not a canonical wire or repository truth format. The planner adds no YAML dependency and validators do not accept YAML artifacts. A future authoring UI may support `YAML -> strict parser -> canonical JSON normalization -> validation -> hashing and transport`, but the normalized JSON is the sole authority. Divergent JSON and YAML copies are forbidden.

## Markdown

Markdown is canonical for human and local-agent instructions: `AGENT_HANDOFF.md`, `PATCH_SPEC.md`, `BEHAVIOR_CONTRACT.md`, `VALIDATION_REPORT.md`, and human reports. `AGENT_HANDOFF.md` remains a Markdown execution contract and is not replaced by JSON or YAML. Machine identity inside the handoff must exactly match `manifest.json`.
