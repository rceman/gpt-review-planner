# Agent Prompt: Direct Session Control

Implement only the registered project-session transport described by `docs/DIRECT_AGENT_SESSION_CONTROL_POLICY.md`.

Provide bounded `agent_send`, `agent_tail`, and `agent_status` operations with serialized sends, structured delivery receipts, no implicit retry, and no generic shell. Reject arbitrary session keys. Prove that the transport performs no task creation, run creation, plan mutation, Git mutation, repository mutation, release authorization, merge authorization, or implementation authorization. Durable work remains in the canonical task/run/completion workflow.
