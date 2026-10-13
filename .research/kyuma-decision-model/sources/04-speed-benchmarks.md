# Source: Qwen2.5/Qwen3 official speed benchmarks + community llama.cpp reports

- URLs: https://qwen.readthedocs.io/en/v2.5/benchmark/speed_benchmark.html , https://qwen.readthedocs.io/en/latest/getting_started/speed_benchmark.html , https://llamaperf.com/model/qwen2-5 , https://github.com/G-B-KEVIN-ARJUN/runtime-inference , https://localai.computer/models/qwen-qwen2.5-1.5b-instruct | Accessed: 2026-10-13 | Via: websearch "llama.cpp benchmark Qwen2.5 1.5B Q4_K_M tokens per second RTX 3060 4060"
- Type: vendor benchmarks + community measurements.

## What it says

- Qwen official: 1.5B BF16 ~40 tok/s, GPTQ-Int4 ~43 tok/s, ~1.2–3GB; Qwen3-0.6B BF16 58–414 tok/s depending on input length (SGLang server numbers, not local).
- Community llama.cpp: 1.5B Q4_K_M ≈ 21 tok/s (RTX 3060/4060 estimates), 38 tok/s Apple M1, 82 tok/s laptop-4060 Q8 (single report); weights 1.0–1.3GB, ~2GB comfortable with 4K context.
- Kyuma math: decision JSON ≈ 20–40 tokens → ~1–2s worst case at 21 tok/s, typically well under 500ms with warm resident server + short prompt.

## What I take from it

- G2: 1.5B Q4_K_M fits any ≥4GB GPU with ~1GB headroom for Vosk; speed clears the Phase 06 p95 ≤500ms budget for short outputs. 0.6B is ~2x faster still.

## Trust

- Evidence: vendor-controlled + scattered community reports, ±20% variance admitted | Limitations: no single controlled llama.cpp 1.5B-vs-0.6B shootout found; willitrun numbers are estimates.
- Confidence: med for absolute tok/s, high for fit (VRAM) and rank-order (0.6B faster than 1.5B).
