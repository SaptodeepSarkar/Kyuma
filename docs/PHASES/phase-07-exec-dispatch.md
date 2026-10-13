# Phase 07 — exec-dispatch

GOAL: Dispatcher validates `Exec`, routes to the right capability, always answers 200/error.

BUILD: `executor/` router: schema-validate → capability handler (stubs OK until 08–13 fill
them) → `Result`. Unknown action → error `Result`, no exception escapes.

GATE (`tests/phase-07/`):
- `test_route_all.py` — one valid `Exec` per 8 actions → reaches correct stub handler.
- `test_invalid.py` — malformed `Exec` (bad action, missing args) → error `Result`, exit 0.
- `test_handler_crash.py` — handler raises → error `Result`, dispatcher stays alive.
- `test_contract.py` — every response matches `Result` schema from Phase 01.
