# Tool-Contract Integrity Policy

The advertised MCP input schema MUST equal the live handler arguments. Every advertised valid request must be accepted, and obsolete or unknown arguments must be rejected consistently. Structured successful output MUST conform to its advertised `outputSchema`.

Where practical, tool registration, schemas, handlers, and documentation derive from one canonical manifest. Fixed magic tool counts are forbidden. Release gates MUST test `tools/list` and `tools/call` parity, required tool names, representative live calls, input schemas, and output schemas. Capability documentation must describe the installed runtime.

Verification MUST distinguish the authoritative configured remote branch/ref from an incidental local checkout `HEAD`. A successful source test suite does not prove an installed binary, running process, protocol surface, or tool schema is the deployed one.
