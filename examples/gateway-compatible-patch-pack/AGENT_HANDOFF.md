# AGENT_HANDOFF

## TASK_IDENTITY

- Patch ID: `patch-20260728-120000-gateway-compatible`
- Workflow repository: `https://github.com/rceman/gpt-review-planner`
- Workflow version: `v1.2.0`
- Workflow commit: `723a8f2a10b9413dadedaf225ad9921eca6b0d4b`
- Workflow document: `GPT_REVIEW_PLANNER.md`
- Target repository: `example/gateway-compatible`
- Target branch: `main`
- Base revision: `1111111111111111111111111111111111111111`
- Evidence directory: `.gpt-review/evidence/v1.2.0/patch-20260728-120000-gateway-compatible`

## AUTHORITY

This handoff and `manifest.json` are the task authority below current owner instructions. This file is the only normative execution entry point.

## AGENT_ROLE

Apply the supplied deterministic fixture as a constrained repository operator and runtime validator.

## PROHIBITED_ACTIONS

Do not broaden scope, add transport fields, merge, tag, release, or rewrite history.

## PATCH_APPLICATION

Verify identity and copy `overlay/demo.txt` to `demo.txt`.

## REQUIRED_RUNTIME_GATES

Run every manifest gate and exact-scope verification. Shell redirection such as `2>errors.log` and comparisons such as `1 < 2` are valid text. An XML fragment such as `<fixture/>` is also valid.

## REPAIR_POLICY

Make only directly evidenced narrow integration repairs and record deviations.

## EVIDENCE_AND_COMMITS

Create an implementation commit followed by an exact two-file direct-child evidence commit.

## TERMINAL_OUTPUT_PROTOCOL

This gateway-managed fixture is complete only after a strict `agent-result.json` is written and the generated `complete-task` command exits successfully. Interactive session text does not complete the task. Finalize `succeeded`, `needs_gpt_revision`, and `failed` outcomes through the same command.

## RESPONSE_CONTRACT

Return the complete execution report in English with commands, gates, commits, deviations, and final repository state.
