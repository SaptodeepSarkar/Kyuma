# Phase 02 — vad-gate

GOAL: Mic input is split into speech vs silence; silence downstream is zero-cost.

BUILD: VAD on live mic (or wav-file input for tests). Emits `speech` chunks; on silence emits
nothing — no empty STT calls, per harness canvas ("Nothing is Spoken → No text output").

GATE (`tests/phase-02/`):
- `test_silence.py` — 5s silence file → zero STT invocations (count via stub counter).
- `test_speech.py` — speech file → at least one chunk emitted.
- `test_mixed.py` — alternating speech/silence → chunks only during speech windows.
