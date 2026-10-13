# Source: official Qwen3 docs — GGUF, thinking control, tool use

- URLs: https://huggingface.co/Qwen/Qwen3-0.6B-GGUF , https://github.com/qwenLM/qwen3 , https://qwenlm.github.io/blog/qwen3/ | Accessed: 2026-10-13 | Via: websearch "Qwen3 0.6B 1.7B GGUF llama.cpp tool calling enable_thinking false function call"
- Type: official vendor docs.

## What it says

- Official GGUFs exist: Qwen/Qwen3-0.6B-GGUF (0.6B, 28 layers, 32K ctx, Apache 2.0), Qwen3-1.7B-GGUF. llama.cpp ≥ b5401 recommended.
- Thinking is ON BY DEFAULT. Disable paths: `enable_thinking=False` in `apply_chat_template` (hard switch, ignores /think), or `/no_think` soft switch per-turn. Qwen3-2507 Instruct variants are non-thinking only.
- Sampling: non-thinking mode suggests Temp 0.7/TopP 0.8/TopK 20; presence_penalty 1.5 recommended for quantized models to suppress repetition.
- Tool calling supported via Qwen-Agent; Qwen3-1.7B/4B-class ≈ larger Qwen2.5 (1.7B ≈ 3B); 119 languages.

## What I take from it

- G7: exact mechanism confirmed — Phase 05/06 MUST set enable_thinking=False (or use -2507 weights), else latency explodes with think tokens. Temp: use 0 for determinism (our gate), not vendor 0.7.
- Qwen3-0.6B-GGUF official = no third-party weight risk for the default candidate.

## Trust

- Evidence: official vendor documentation.
- Confidence: high.
