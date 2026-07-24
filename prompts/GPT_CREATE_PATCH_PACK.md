# GPT: Create Executable Patch Pack

Use the workflow pinned by the target repository's `.gpt-workflow.lock`.

Inspect the repository or supplied archive and prepare an Executable Patch Pack.
Own the architecture, behavior contract, canonical fixtures, native tests,
principal production implementation, file-by-file patch, static review report,
agent prompt, and acceptance gates.

GPT may perform static repository and artifact checks: archive integrity,
manifest and patch/overlay/file-scope consistency, placeholder scans, textual
or AST inspection, and syntax-only checks that do not compile or execute project
code.

GPT must not install or update dependencies, compile or build the project, run
formatters or project linters, execute unit/integration/E2E/property tests,
benchmarks, runtime smoke tests, or start project services. GPT must not claim
runtime validation based on its own sandbox execution. If `rustc` is missing,
record that runtime validation is not executed by GPT; do not bootstrap a
compiler merely to run tests.

Do not leave ordinary implementation work, TODOs, pseudocode, missing tests,
or unresolved architecture decisions to the local agent. Leave only dependency
restoration, environment integration, compilation, runtime test execution,
evidence collection, and minimal integration corrections.

The validation report must contain these sections:

```text
GPT_STATIC_CHECKS_PERFORMED
GPT_RUNTIME_CHECKS_NOT_PERFORMED
AGENT_RUNTIME_GATES_REQUIRED
AGENT_RUNTIME_RESULTS
```

Set `AGENT_RUNTIME_RESULTS` to `Pending local-agent execution.` in the authored
pack. The local agent replaces it with exact commands, results, and evidence.

The manifest, `changes.patch`, overlay, deletion list, and expected final repository
diff must describe the same path scope. Include the pending `evidence.json` template,
`patch_pack_scope.py`, and `verify-agent-evidence.py` in every canonical pack.
Validate exact scope before archiving.

## Required identity and evidence contract

Create schema-v2 manifests with a UTC timestamp ID, concise title and description, last published target baseline tag, exact evidence directory, stable requirement IDs with acceptance criteria, and compact required gate definitions.

Include a pending `evidence.json` template whose requirement and gate IDs exactly match the manifest. Include pinned copies of `patch_pack_scope.py` and `verify-agent-evidence.py`. Do not create Markdown agent-result or deviation templates. Do not infer the baseline tag from an unreleased version file.
