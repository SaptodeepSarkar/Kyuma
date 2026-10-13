# Source: Chinese latency-sensitive model-selection study (jishuzhan.net)

- URL: https://jishuzhan.net/article/2066322367470727169 | Accessed: 2026-10-13 | Via: websearch "Qwen3-0.6B vs Qwen2.5-1.5B tool calling accuracy VRAM speed local inference"
- Type: practitioner benchmark | Setup: Qwen2.5-0.5B/1.5B/3B + Qwen3-1.7B, CPU vs GPU, 50 tool-selection queries x 10 tools, 30 extraction msgs x 5 intents.

## What it says

- Tool selection Top-1 (GPU): 0.5B 56% / 1.5B 92% / Qwen3-1.7B 88% / 3B 96%; p50 latency GPU: 63ms / 94ms / 109ms / 156ms.
- Extraction value-match: 1.5B 83% (failures = "empty-schema stuffing": emitting params where none belong); 3B and Qwen3-1.7B 100%.
- Conclusion: GPU mandatory (CPU 8–16x slower); 1.5B is the sweet spot; 0.5B abandoned (too dumb to fix with SFT).

## What I take from it

- G1+G2 together: 1.5B-class hits 92% Top-1 at ~94ms p50 on GPU — directly supports the Phase 06 gate (≥95% + p95 ≤500ms) as realistic.
- Kyuma parallel: our 8 intents ≈ their 10 tools; their "empty-schema stuffing" failure is exactly what GBNF + required-fields fixes.

## Trust

- Evidence: controlled experiment, n=50+30, real latency numbers | Limitations: Chinese-language, single author, unknown GPU model.
- Confidence: med-high.
