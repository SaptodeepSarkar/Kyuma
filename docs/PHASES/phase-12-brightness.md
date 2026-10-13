# Phase 12 — brightness

GOAL: Reliable brightness get/set via backlight control.

BUILD: `brightness {get|set|up|down}` (brightnessctl — document choice). Clamp to device
min/max; never set 0-blind without an explicit confirm path (document it).

GATE (`tests/phase-12/`, require backlight device; else skip with reason):
- `test_set.py` — set 50% → reads back 50%.
- `test_clamp.py` — set 200% → error `Result`, unchanged.
- `test_up_down.py` — up/down moves by the documented step.
- `test_no_blackout.py` — `set 0` path requires explicit flag, plain `set 0` rejected or clamped.

NOTES (as built):
- Backend: `brightnessctl -c backlight` (kernel backlight class; this machine:
  `nvidia_wmi_ec_backlight`, max 800). Raw `/sys` writes (root), `ddcutil`
  (external monitors), `light` (unmaintained) rejected.
- Step: `STEP_PCT = 10` (`executor/brightness.py`); up/down = `set +10%` / `10%-`.
- Zero-guard: plain `set {"value": 0}` → error `Result`, device untouched.
  Full blackout needs explicit `{"value": 0, "force": true}` (`-n 0 set 0`).
