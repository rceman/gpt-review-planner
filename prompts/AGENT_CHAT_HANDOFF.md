# Agent Prompt: Chat Handoff

Load `docs/CHAT_HANDOFF_CHECKPOINT.md` and produce a self-contained checkpoint before changing conversations. Include repository URLs and paths, exact SHAs for main and feature refs, versions/tags, installed/running versions, gateway/tunnel PIDs, authoritative hub repo/branch/SHA, MCP tool names and schema-parity status, durable plan revision, task/run/completion state, architecture decisions, compatibility scope, incident lessons, validation commands, known risks, authorization boundaries, and the exact next action.

Carry the pinned `docs/OWNER_COMPLETION_REPORT.md` policy in the handoff. The
receiving GPT must apply it when presenting terminal work to the owner; this
exhaustive checkpoint remains technical handoff evidence, not the owner-facing
report.

Freeze the checkpoint before transition. Do not start another feature phase between the checkpoint and the next conversation. Preserve the single completion authority and state whether merge, release, or gateway integration is authorized.
