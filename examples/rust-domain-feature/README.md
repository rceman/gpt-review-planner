# Example: Rust Domain Feature Patch

This example demonstrates:

- target-language production code;
- native Rust unit tests;
- a standard-library Python oracle;
- shared JSON fixtures;
- separation between validated domain logic and repository integration.

The example is intentionally small. Its purpose is to show artifact shape and
responsibility boundaries, not to prescribe a game-specific damage formula.

## Quick validation

From the workflow repository root:

```bash
bash scripts/bootstrap-rustc.sh -- bash -lc '
  rustc --edition=2021 --test \
    examples/rust-domain-feature/overlay/src/damage_kernel.rs \
    -o /tmp/damage-kernel-tests
  /tmp/damage-kernel-tests
'

python -m unittest discover \
  -s examples/rust-domain-feature/reference/python -v
```
