# Phase 04 — buffer-complete

GOAL: Fragments accumulate; the harness fires exactly once per complete command.

BUILD: `harness/` buffer (ARRAY): append each `Word`; completeness check (length/punctuation/
timeout heuristic — document the rule chosen). Incomplete → keep waiting. Complete → emit
sentence downstream, stop appending to that batch.

GATE (`tests/phase-04/`):
- `test_accumulate.py` — feed "switch", "to", "workspace three" → one sentence out, not three.
- `test_no_partial_fire.py` — single word "switch" → nothing emitted downstream.
- `test_timeout.py` — stalled fragment flushes/discards after timeout (document which).
- `test_rapid_commands.py` — two back-to-back sentences → two separate emissions, no merge.
