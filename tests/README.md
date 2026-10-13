# tests/ — phase gates

No phase in `docs/PHASES/` is done until its goal is met AND every gate test listed in its
phase doc passes. No skipping forward.

## Layout

- `tests/phase-NN/` — gate tests for that phase, named `test_*.py` (pytest default).
- `tests/gate.sh <NN>` — runs one phase's gates, exits non-zero on any failure.

## Rules

- Gate tests are written when the phase starts, pass when it ends.
- A gate must fail on the pre-phase code (prove it tests something) — no tautologies.
- Hardware gates (mic, GPU, Hyprland) skip cleanly with a reason when the resource is absent;
  a skip is not a pass — note it in the phase doc.
