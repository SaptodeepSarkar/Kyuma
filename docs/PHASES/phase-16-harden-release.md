# Phase 16 — harden-release

GOAL: Proven realtime + documented. Release only when the budget holds and docs match code.

BUILD: Latency budget from Phase 14 logs (target: word → action ≤ ~1s on local GPU).
10-minute spoken soak: mixed commands + silence + gibberish. Sync `docs/` + vault
`Projects/Kyuma/` (flows, PRDs) to what was actually built; note every deviation.

GATE (`tests/phase-16/`):
- `test_latency_budget.py` — p95 word→action within budget on the fixture script.
- `test_soak.py` — 10-min scripted run: zero crashes, zero stuck buffers, error rate logged.
- `test_gibberish_soak.py` — random speech never triggers a destructive action.
- `test_docs_match.py` — every capability in code appears in `docs/` + vault note (manual
  checklist with sign-off line counts as this test's pass).
