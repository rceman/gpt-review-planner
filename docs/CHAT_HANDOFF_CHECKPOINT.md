# Chat Handoff Checkpoint

Before moving to a new ChatGPT conversation, freeze a self-contained checkpoint containing:

- repository URLs and local paths;
- exact main SHAs, feature SHAs, versions, and tags;
- installed and running versions, gateway/tunnel PIDs, and authoritative hub repository/branch/SHA;
- MCP tool surface and schema-parity result;
- active durable plans and task/run state;
- architecture decisions, compatibility scope, incident lessons, validation commands, and known risks;
- the pinned [`OWNER_COMPLETION_REPORT.md`](OWNER_COMPLETION_REPORT.md) policy and its separation from machine evidence;
- the exact next action and its authorization.

No new feature phase may begin between handoff freeze and chat transition. A handoff must identify the one completion authority, exact refs, current worktree state, and whether release, merge, or gateway integration is authorized. The exhaustive checkpoint is technical handoff evidence, not the user-facing report; the receiving GPT applies the pinned owner-report policy.
