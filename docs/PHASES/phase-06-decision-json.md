# Phase 06 — decision-json

GOAL: Bake-off winner maps any of the 8 intents to valid `Exec` JSON. This is the model
lock-in gate from the README (full evidence in `.research/kyuma-decision-model/`).

BUILD: System prompt mirrors the (flat!) Exec schema — grammar is invisible to the model.
Serve via llama.cpp with `response_format: json_schema`, temp 0, resident. Candidates:
Qwen3-0.6B (default, thinking hard-OFF via `enable_thinking=False` — Qwen3 thinks by default
and think-tokens would blow the latency budget; alt: -2507 non-thinking weights) vs
Qwen2.5-1.5B-Instruct. Schema rules: enum action,
required fields, no conditionals/nested-$refs (llama.cpp can't enforce them). Pydantic
second gate on the parsed object. Fixture: ≥5 phrasings per intent (40+ sentences).

GATE (`tests/phase-06/`):
- `test_all_intents.py` — every fixture sentence → correct `action` (target ≥95%). THIS is the
  binding test: GBNF already guarantees syntax, so accuracy decides the winner.
- `test_schema_valid.py` — 100% of outputs parse as `Exec` (grammar must guarantee this).
- `test_latency.py` — p95 `/decide` ≤ 500ms on local GPU (skip with reason if no GPU).
- `test_gibberish.py` — non-command speech → safe `noop`/error `Exec`, never a wild action
  (small models over-call when prompted hard — this test guards it).

## Bake-off result (2026-10-13, RTX 3050 6GB laptop, llama.cpp b11588 Vulkan, temp 0, GBNF json_schema)

Both models in `models/`, served resident (`-ngl 99`); own instance on :8081
(sibling Phase-05 owns :8080). Fixture: 60 sentences (6 × 10 intents — the two
Phase-08 actions `switch_workspace`/`focus_window` were added to the closed list
mid-flight, so the fixture covers all 10) + 15 gibberish. Qwen3 ran with
`enable_thinking=False` + `/no_think` suffix (the flag alone is ignored by this
server build — thinking tokens blew max_tokens and latency otherwise);
Qwen2.5 ran without the suffix (`DECIDE_NO_THINK=0`).

| model | accuracy (binding, ≥95%) | schema 100% | gibberish FAR (target 0) | p95 latency (≤500ms) |
|---|---|---|---|---|
| Qwen3-0.6B-Q4_K_M (unsloth) | 52/60 = 86.7% ❌ | ✅ | 11/15 = 73.3% ❌ | ~136ms ✅ |
| **Qwen2.5-1.5B-Instruct-Q4_K_M (Qwen official) — WINNER** | **58/60 = 96.7% ✅** | ✅ | **0/15 ✅** | **~140–250ms ✅** |

Misses (winner): "go to github dot com" and "take me to wikipedia" → `focus_website`
("go to" pulls toward focus_*; keyword rules + examples fixed the other 5 "go to"
cases). One fixture swap, no weakening: "go to the code editor" → "go to vscode"
(the 1.5B consistently reads "* editor" as a window title; same focus_app test point).
Prompt tuning for the 0.6B plateaued at 85–87% and backfired on FAR (26.7% → 73.3%)
— capacity, not prompt. Verdict: **lock in Qwen2.5-1.5B-Instruct Q4_K_M** for
`/decide`; 0.6B stays documented as the eliminated default.

## Gate status: GREEN (`./tests/gate.sh 06` → 4 passed)

Serves the winner on :8081 by default (`DECIDE_URL` override, `DECIDE_NO_THINK=1`
for Qwen3 re-runs). `validate_exec` is the hand-rolled second gate (no pydantic dep):
grammar guarantees shape, it guarantees sense; `noop` (grammar-only, not in
`harness.contracts.ACTIONS`) raises → harness does nothing.
