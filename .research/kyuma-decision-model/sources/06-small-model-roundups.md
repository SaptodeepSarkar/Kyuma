# Source: 2026 small-model roundups (vdf.ai SLMs, graysoft head-to-head, heyneo CPU bench, obakavv local-FC report)

- URLs: https://vdf.ai/blog/best-small-language-models/ , https://graysoft.dev/models/compare/llama-3-2-1b-intruct-tool-calling-v2-q8-0-vs-qwen3-0-6b-q8-0 , https://heyneo.com/blog/needle-26m-vs-qwen3-0.6b-cpu-function-call-benchmark , https://note.com/cool_magpie9305/n/n002670ab28b8 | Accessed: 2026-10-13 | Via: the three hunt sweeps above.
- Type: independent comparisons.

## What it says

- graysoft (32 agentic tests): Qwen3-0.6B 84% vs Llama-3.2-1B-toolcalling-tune 55% — 29pt gap, smaller model wins.
- heyneo (50 queries, CPU): prompted Qwen3-0.6B 84% tool-match / 100% parse; strong system prompt matters more than size at this scale; over-eager tool-calling is the failure mode to gate against (matches our gibberish test).
- obakavv: Qwen3 leads FC at every size 8B→32B; JSON-schema compliance NOT in BFCL — enforce via GBNF/Outlines in practice.
- vdf.ai: Qwen3.5-4B matches 9B on TAU2; scores climb steeply sub-1B→4B; Llama 3.2 smalls are "long-established" but not leaders; all picks Apache 2.0/MIT except Llama.
- Licenses: Qwen3/Qwen2.5 Apache 2.0 (official Qwen blog + HF); Llama 3.2 community license (700M-MAU clause); xLAM-2 restricted — reject for Kyuma.

## What I take from it

- G4: shortlist = Qwen3-0.6B (fastest, newest, 84%-class) vs Qwen2.5-1.5B-Instruct (bigger margin, mature GGUF ecosystem) vs sagnik 1.5B-FC finetune (highest claimed accuracy, third-party risk). Eliminated: all Llama-3.2 smalls, xLAM-2 (license), 0.5B-class (too weak), ≥3B (VRAM/speed cost vs Vosk coexistence).

## Trust

- Evidence: multiple independent parties converging on Qwen-small > Llama-small | Limitations: heterogeneous harnesses, some vendor-adjacent.
- Confidence: high for shortlist, med for exact ordering — Phase 06 bake-off decides.
