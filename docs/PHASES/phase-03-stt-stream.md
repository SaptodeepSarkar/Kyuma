# Phase 03 — stt-stream

GOAL: Words stream out at ~1 RTF with a swappable Vosk model.

BUILD: `stt/` loader takes model path from config (default Vosk Indian model). Streaming
recognizer emits partial/final `Word`s. No hardcoded model paths anywhere.

GATE (`tests/phase-03/`):
- `test_streaming.py` — sample wav → partial results arrive before final (not one batch).
- `test_rtf.py` — RTF ≤ ~1.2 on sample audio (skip with reason if no audio/GPU in CI).
- `test_swappable.py` — point config at a second model dir → loads and transcribes (may skip
  if only one model downloaded; then assert the config path is honored, not default).
- `test_silence_empty.py` — VAD silence chunk → no words out.

## Build notes (Wave 1/Phase 03, 2026-10-13)

- Backend: `vosk==0.3.45` from PyPI (has 3.14 wheels — no source build needed).
- Models in `models/`: default `vosk-model-small-en-in-0.4` (~36MB), second
  `vosk-model-small-en-us-0.15` for the swappability gate. `tried
  vosk-model-tiny-en-us-0.22 — URL 404s, used small-en-us instead`.
- `stt/loader.py`: arg > `KYUMA_STT_MODEL` env > repo-relative default. No
  hardcoded paths at call sites. `stt/stream.py`: `StreamingRecognizer.push`
  returns `(partial, final)` `Word{w, t}` lists; `transcribe_wav` yields
  `"partial"|"final"` events. Consumes raw chunks (`stt/vad.py` absent —
  Phase 02 not landed; interface matches its doc: speech chunks in).
- Sample: `tests/phase-03/sample.wav` (30s, 16kHz mono, ~0.9MB, open-speech
  passages concatenated via ffmpeg).
- Gate `./tests/gate.sh 03`: 5 passed. Measured RTF ≈ 0.1–0.2 (≤ 1.2).
  126 nonempty partials precede finals on the sample — streaming proven.
