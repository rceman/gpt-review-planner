# AGENT_HANDOFF

## TASK_IDENTITY

- Patch ID: `TEMPLATE_PATCH_ID`
- Workflow repository: `TEMPLATE_WORKFLOW_REPOSITORY`
- Workflow version: `TEMPLATE_WORKFLOW_VERSION`
- Workflow commit: `TEMPLATE_WORKFLOW_COMMIT`
- Workflow document: `TEMPLATE_WORKFLOW_DOCUMENT`
- Target repository: `TEMPLATE_TARGET_REPOSITORY`
- Target branch: `TEMPLATE_TARGET_BRANCH`
- Base revision: `TEMPLATE_BASE_REVISION`
- Evidence directory: `TEMPLATE_EVIDENCE_DIRECTORY`

## AUTHORITY

Apply authority in this order: current owner instructions, this handoff and manifest, the exact pinned workflow, repository `AGENTS.md`, then existing repository conventions. This file is the only normative local-agent execution entry point.

## AGENT_ROLE

Act as repository operator and runtime validator. Apply the supplied implementation, run every declared gate, make only directly evidenced narrow integration repairs, and preserve the approved behavior and exact scope.

## PROHIBITED_ACTIONS

Do not redesign approved behavior, weaken tests or acceptance criteria, broaden scope, add dependencies without authorization, merge, tag, release, rebase, squash, amend, reset, force-push, rewrite history, or modify unrelated repositories.

## PATCH_APPLICATION

Verify the exact repository and base revision. Apply `patch/changes.patch`, `overlay/`, and `patch/delete-paths.txt` according to the manifest. Stop on identity, scope, or application mismatch.

## REQUIRED_RUNTIME_GATES

Run every gate declared by `manifest.json`, followed by exact scope verification and repository cleanliness checks. Record exact commands, exit codes, test counts, and artifact paths.

## REPAIR_POLICY

Repairs are limited to defects directly demonstrated by patch application, compilation, formatting, or tests. Preserve semantics and add regression coverage for every non-formatting repair. Stop when correction requires scope expansion or owner decision.

## EVIDENCE_AND_COMMITS

Create one implementation commit containing only the declared implementation scope. Then generate exactly `manifest.json` and `evidence.json` in the declared evidence directory, verify prepare mode, create one direct-child evidence-only commit, verify committed mode, and push the feature branch without rewriting history.

## TERMINAL_OUTPUT_PROTOCOL

This is a gateway-managed GPT task. Interactive Airelay/Codex text does not complete it. Before ending for `succeeded`, `needs_gpt_revision`, or `failed`, write the strict gateway-authoritative `agent-result.json`, then invoke the exact gateway-generated `complete-task` command appended at runtime. Do not ask the owner for approval or clarification. Do not replace the finalizer with hand-written Git, JSON, or bus verification commands.

## RESPONSE_CONTRACT

Write the concise structured result in English. Record status, summary/details, implementation and evidence SHAs when successful, every declared gate, deviations, and the next GPT action when revision is required. Derived repository, branch, worktree, remote, timestamp, and bus facts are gateway-owned. Do not merge, tag, or release.
