# Phase 01 — scaffold-contracts

GOAL: Repo skeleton exists and every later phase speaks the same message shapes.

BUILD: Create `stt/ harness/ executor/ model-server/ ui/ tests/phase-01/`. Decide language +
IPC (default: Python + local HTTP/JSON unless a phase proves otherwise). Freeze three schemas:
`Word{w:text, t:float}`, `Exec{action:str, args:dict}`, `Result{code:200|error, detail:str}`.

GATE (`tests/phase-01/`):
- `test_layout.py` — all six dirs + this doc exist.
- `test_schemas.py` — valid/invalid samples for all three schemas (reject bad `Exec.action`).
- `test_ipc_ping.py` — harness ↔ executor round-trip returns `Result` (stub ends allowed).
