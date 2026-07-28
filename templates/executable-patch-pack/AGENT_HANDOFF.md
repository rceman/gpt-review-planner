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

## RESPONSE_CONTRACT

Write the complete execution response in English. Report base, implementation and evidence SHAs, every gate, repairs, deviations, CI evidence, remote branch state, VERSION, and worktree state. Do not merge, tag, or release.
