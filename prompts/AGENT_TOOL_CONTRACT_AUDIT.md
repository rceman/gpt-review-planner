# Agent Prompt: Tool-Contract Audit

Load `docs/TOOL_CONTRACT_INTEGRITY_POLICY.md`. Compare the live `tools/list` surface with handler signatures and advertised input schemas. Exercise every required tool and representative valid/invalid calls. Verify structured successful output against `outputSchema`.

Reject obsolete arguments consistently, reject unknown arguments, and ensure registration, schemas, handlers, documentation, and capability output derive from the same canonical manifest where practical. Do not assert a fixed tool count. Verify the configured authoritative remote branch/ref rather than an incidental checkout `HEAD`, and record exact tool names and schema-parity results.
