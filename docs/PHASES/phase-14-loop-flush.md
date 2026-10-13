# Phase 14 — loop-flush

GOAL: The full canvas loop runs live: speech → words → sentence → Exec → action → flush,
on 200 AND on error, without blocking speech.

BUILD: Wire 02→03→04→06→07→(08–13). Flush buffer after every dispatch regardless of result.
Log each hop with timestamps (feeds Phase 16 latency audit).

GATE (`tests/phase-14/`):
- `test_happy_path.py` — scripted sentence "volume up" end-to-end → volume changes, 200 logged.
- `test_flush_on_error.py` — command that errors → buffer empty after, next command unaffected.
- `test_no_stale_words.py` — two rapid commands → second uses only its own words.
- `test_speech_not_blocked.py` — slow model stub (2s) → STT words still buffer during the wait.

BUILT (Wave 4):
- `harness/loop.py` — `run_once(words, decide_fn=None, log=None) -> Result | None`:
  shared `Buffer`, utterance-end force-emit (so 2-word "volume up" dispatches),
  default decide = wrapper `POST /decide`, `noop` → 200 without dispatch,
  never raises, per-hop `{t, hop, detail}` log. Flush removes only the
  dispatched words by identity, so arrivals during a slow decide survive.
  `ingest()` buffers without dispatching (STT streaming path).
- `executor/__init__.py` — `register_all()` (idempotent): imports
  hyprland/apps/browser/volume/brightness (+ music if present) and binds real
  handlers for volume/brightness/switch_workspace/focus_window (apps/browser
  self-register on import). Deliberately NOT import-time: eager registration
  would replace the stubs gate 07 asserts. Called by `harness.loop`.
- `tests/phase-14/` — conftest reuses wrapper :8081 if `{"loaded": true}`,
  else spawns the wrapper (phase-05 helper) on an ephemeral port, else stub
  decide; audio snapshot/restore; `words()` scripted-Word factory.

RESULTS (this box): gate 14 GREEN 5/5 — happy path ran LIVE (spawned wrapper,
Qwen2.5-1.5B): 40% → 45%, 200 logged, word→action 350.8 ms (stub-only: 18.3 ms).
Gates 01–04, 07–12 re-run GREEN (07: 16/16 — stubs intact). 05/06 untouched,
not re-run (long bake-off; no shared files changed).
- One transient mixer read (0.42, unreproduced; rapid set/up cycles exact at
  0.40→0.45) led to a verify-and-retry in the audio-restore fixture.
- Known arg-shape gaps (out of scope): decide-prompt emits
  `open_app{app}` vs handler `{name}`, `open_website{site}` vs `{url}`,
  `focus_window{window}` vs `{class|title}`, `brightness{level}` vs `{value}` —
  live volume path verified; other actions need Phase 16 arg normalization.
