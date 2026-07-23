# Local Agent: Apply Patch Pack

Load `AGENTS.md`, `.gpt-workflow.lock`, and the exact pinned GPT Review Planner.

Read the complete patch pack, verify the repository and base revision, apply the
GPT-authored implementation, restore dependencies, and run all required gates.

Do not redesign approved behavior or weaken tests. Correct only verified
integration defects inside the declared file scope, add regression coverage for
each correction, maintain `DEVIATIONS.md`, run the pack scope verifier, and produce
exact command and result evidence. Stop before merge when an undeclared path is
required.
