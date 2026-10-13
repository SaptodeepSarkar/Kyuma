# Phase 11 — volume

GOAL: Reliable volume get/set/mute via the system mixer.

BUILD: `volume {get|set|up|down|mute|unmute}` (wpctl/pactl — document choice). Clamp 0–100%;
`set` outside range → error, volume unchanged.

GATE (`tests/phase-11/`, require audio stack; else skip with reason):
- `test_set.py` — set 42 → mixer reads 42.
- `test_clamp.py` — set 150 → error `Result`, volume unchanged.
- `test_mute_cycle.py` — mute → muted; unmute → restores prior level.
- `test_up_down.py` — up/down moves by the documented step.

BUILT: `executor/volume.py` — `wpctl` (native PipeWire/WirePlumber CLI, default-sink
addressing; `pactl` rejected as Pulse-compat indirection). `STEP = 5` (% points;
`up` capped at 100% via `wpctl -l 1.0`). Mute is a PipeWire flag so the mixer
preserves the level — unmute restores it with no bookkeeping.
