# Validation Report

## GPT_STATIC_CHECKS_PERFORMED

- Reviewed the standalone Rust kernel, Python oracle, fixtures, and example
  paths statically.

## GPT_RUNTIME_CHECKS_NOT_PERFORMED

- GPT did not bootstrap Rust, compile the kernel, or execute either test suite.

## AGENT_RUNTIME_GATES_REQUIRED

The local coding agent must execute the Rust test command and the Python oracle
command shown in `README.md`, then record their exact outputs.

## AGENT_RUNTIME_RESULTS

Pending local-agent execution.

| Gate | Written by GPT | Executed by agent | Result | Evidence or log location |
|---|---|---|---|---|
| Rust standalone tests | test source and command | pending | pending | pending |
| Python oracle tests | test source and command | pending | pending | pending |

## Residual integration surface

The repository-specific `mod.rs` export and call-site adapter are intentionally
not represented in this generic example. A real patch pack must include them.
