# Phase 05 — model-server

GOAL: Model stays resident behind a local API; harness never loads weights.

BUILD: `model-server/` with endpoints: `POST /decide {sentence} → Exec`, `GET /health`
(loaded?, device, VRAM). Handles GPU placement, context reset, CPU offload fallback.
Serve any tiny stub model here — real weights land in Phase 06.

Weights (decided Phase 06 bake-off, 96.7%): default
`models/qwen2.5-1.5b-instruct-q4_k_m.gguf`; backup
`models/Qwen3-0.6B-Q4_K_M.gguf` via `--model` (thinking-off `/no_think`
kept harmlessly for it). Backend: llama.cpp b11588 CUDA prebuilt in
`model-server/vendor/` (+ vendored cudart, no system install); wrapper
`model-server/server.py` owns the child on an ephemeral port, serves the
API on `--port` (default 8080; never 8081 — sibling Phase 06 lives there).
Start: `.venv/bin/python model-server/server.py [--port 8080]`; stop: Ctrl-C
or SIGTERM (child reaped; SIGTERM handled via shutdown thread).

GATE (`tests/phase-05/`):
- `test_resident.py` — two `/decide` calls → model loaded once (no reload between).
- `test_health.py` — `/health` reports device + loaded flag truthfully.
- `test_offload.py` — force CPU/offload config → still answers (slower allowed).
- `test_bad_input.py` — empty sentence → 4xx, no crash, server stays up.
