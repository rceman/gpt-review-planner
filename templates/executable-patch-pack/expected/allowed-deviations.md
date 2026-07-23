# Allowed Deviations

Mechanical integration corrections are permitted when they preserve the behavior contract:

- imports and module registration;
- visibility;
- type conversions;
- trait bounds;
- ownership and lifetime corrections;
- non-semantic framework API drift;
- fixture path resolution;
- test harness integration.

Mechanical corrections are allowed only inside paths already declared in
`manifest.json`. A required change to any additional path is a blocking deviation:
document it in `DEVIATIONS.md`, stop before merge, and request an updated patch pack
or explicit owner approval.
