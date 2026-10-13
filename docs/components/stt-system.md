# STT System

Streaming ASR feeding the Kyuma harness word-by-word.

- Requirement: near 1 RTF (realtime factor) — text must stream, not batch.
- Default model: Vosk Indian model.
- Constraint: modular — any Vosk model must be usable, no hardcoded model path.
- Contract: speech → word stream; silence → no output (VAD-gated, per harness canvas).
