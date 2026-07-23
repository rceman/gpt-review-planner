# GPT: Create Executable Patch Pack

Use the workflow pinned by the target repository's `.gpt-workflow.lock`.

Inspect the repository or supplied archive and prepare an Executable Patch Pack.
Own the architecture, behavior contract, canonical fixtures, native tests,
principal production implementation, file-by-file patch, validation report,
agent prompt, and acceptance gates.

Do not install dependencies or run expensive full-project gates unless required.
Perform every available dependency-free validation. If `rustc` is missing,
use `scripts/bootstrap-rustc.sh` before classifying standalone Rust validation as
unavailable. Do not install the full project environment merely to obtain a
compiler.

Do not leave ordinary implementation work, TODOs, pseudocode, missing tests,
or unresolved architecture decisions to the local agent. Leave only environment
integration, compilation, runtime test execution, evidence collection, and
minimal integration corrections.

The manifest, `changes.patch`, overlay, deletion list, and expected final repository
diff must describe the same path scope. Include `DEVIATIONS.md` and the standalone
`patch_pack_scope.py` verifier in every pack. Validate exact scope before archiving.
