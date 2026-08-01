# Direct Agent Session Control Policy

Direct project-session control is a bounded transport, not durable work. It MUST use a registered project/session; arbitrary session keys and generic shell are forbidden. It performs no task creation, no run creation, no plan mutation, no Git mutation, and no repository mutation.

The supported transport operations are `agent_send`, `agent_tail`, and `agent_status`. They require bounded input/output, serialized sends, no implicit retry, and a structured delivery receipt. A send may continue an already authorized operation, report current status, or provide a bounded tail.

Direct session control MUST NOT authorize implementation, acceptance, release, merge, or durable work. Those actions require the canonical task/run/completion authority and their normal evidence gates.
