# Validation Report

## GREEN

```bash
bash ../../scripts/bootstrap-rustc.sh -- bash -lc '
  rustc --edition=2021 --test overlay/src/damage_kernel.rs \
    -o /tmp/damage-kernel-tests
  /tmp/damage-kernel-tests
'
python -m unittest discover -s reference/python -v
```

The standalone Rust tests and Python oracle tests are expected to pass without
external dependencies.

## YELLOW

The repository-specific `mod.rs` export and call-site adapter are intentionally
not represented in this generic example. A real patch pack must include them.
