# GPT: Create Executable Patch Pack

Use the workflow pinned by the target repository's `.gpt-workflow.lock`.

Read and follow `docs/AGENT_COMMUNICATION_LANGUAGE.md`. All local-agent-facing communication MUST be written in English regardless of the owner's conversation
language. Every generated `AGENT_HANDOFF.md`, correction prompt,
merge/release instruction, and required agent execution report is English.
Preserve exact filenames, commands, identifiers, errors, source excerpts, and
localized repository content without translation; do not create bilingual
agent instructions.

Inspect the repository or supplied archive and prepare an Executable Patch Pack.
Own the architecture, behavior contract, canonical fixtures, native tests,
principal production implementation, file-by-file patch, static review report,
canonical agent handoff, and acceptance gates.

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

Load the pinned bounded review closure protocol. Every manifest requirement MUST
map to an owner-approved acceptance criterion or an explicitly approved
supporting implementation requirement. Preserve the approved scope lock and
finding IDs in the patch specification and agent prompt. Do not add unapproved
hardening merely because it is possible; unapproved hardening remains outside
the current patch.

After agent execution, GPT performs a delta review of approved findings,
changed surfaces, acceptance criteria, required gates, and regressions. It does
not restart an unconstrained full review. Non-blocking discoveries are recorded
as follow-up backlog; when closure conditions pass, declare `MERGE_READY` and
stop.

The manifest, `changes.patch`, overlay, deletion list, and expected final repository
diff must describe the same path scope. Include the pending `evidence.json` template,
canonical `AGENT_HANDOFF.md`, `patch_pack_scope.py`, `verify-agent-evidence.py`,
and `verify-agent-result.sh` in every canonical pack.
Validate exact scope before archiving.

## Required identity and evidence contract

Create schema-v2 manifests with a UTC timestamp ID, concise title and description, last published target baseline tag, exact evidence directory, stable requirement IDs with acceptance criteria, and compact required gate definitions.

Include a pending `evidence.json` template whose requirement and gate IDs exactly match the manifest. Include pinned copies of `patch_pack_scope.py` and `verify-agent-evidence.py`. Do not create Markdown agent-result or deviation templates. Do not infer the baseline tag from an unreleased version file.

`AGENT_HANDOFF.md` is the sole normative execution entry point. Do not generate
a second independently edited `AGENT_PROMPT.md`; a temporary compatibility alias
is permitted only when byte-identical to the handoff.

Every delivered pack must pass `scripts/validate-patch-pack-delivery.py`.

Before delivery, derive the archive basename exactly as `<manifest.patch_id>.tar.gz`
and the sidecar as `<archive>.sha256`. Include exact byte-identical copies of
all three canonical bundled tools from the pinned planner checkout; wrappers and
shims are not permitted. Run them with `--help`, validate the semantic pack in
text and JSON modes, construct a representative fixture, and run the delivery
validator in the applicable `manual-download` or `gateway-task-bundle` mode.
The final actionable response must
print the two plain-text filename fields and end with the exact top-level
`## AGENT_HANDOFF` sentence defined by the handoff contract. Prompt-only and
no-action responses must not claim an archive or runtime result.
Resolve CI policy before adding a GitHub Actions gate. Do not add a mandatory remote-CI gate unless policy is `required`; use `scripts/check-github-ci.py` for observations.
