# Validation Report

The authoritative post-execution record is `evidence.json`; this Markdown file is explanatory only.

## GPT_STATIC_CHECKS_PERFORMED

GPT records static and artifact checks here when creating a pack. Executable quality gates are defined by `manifest.json` and are not represented as completed in this report.

## GPT_RUNTIME_CHECKS_NOT_PERFORMED

Runtime validation is not executed by GPT. The local coding agent owns the gates defined in `manifest.json`.

## AGENT_RUNTIME_GATES_REQUIRED

Required gate definitions and commands are stored once in `manifest.json` under `gates`.

## AGENT_RUNTIME_RESULTS

Before agent execution, results are pending. After execution, compact results are recorded by gate ID in `evidence.json`.
