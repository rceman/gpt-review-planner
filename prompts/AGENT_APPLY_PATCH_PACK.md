# Local Agent: Apply Patch Pack

Load `AGENTS.md`, `.gpt-workflow.lock`, and the exact pinned GPT Review Planner.

Read the complete patch pack, verify the repository and base revision, apply the
GPT-authored implementation, restore dependencies, and run all required gates.
The local coding agent owns every executable quality gate; GPT only performs
static/artifact review and reviews the evidence after execution.

Do not redesign approved behavior or weaken tests. Correct only verified
integration defects inside the declared file scope, add regression coverage for
each correction, record genuine deviations structurally in `evidence.json`, run
the pack scope verifier, and produce exact command and result evidence. Report
`Written by GPT`, `Executed by agent`, `Result`, and `Evidence or log location`
separately. Stop before merge when an undeclared path is required.

## Required committed JSON evidence

After all runtime gates pass, create the implementation commit. Create the exact directory from `manifest.evidence_directory`, copy `manifest.json` byte-for-byte, and complete compact `evidence.json` with the implementation SHA, every requirement and proof, every gate result, and any structured deviations.

Run `verify-agent-evidence.py prepare`, commit exactly `manifest.json` and `evidence.json`, then run `verify-agent-evidence.py committed`. Never record the evidence commit SHA inside evidence and never repeat commands already defined in the manifest.
