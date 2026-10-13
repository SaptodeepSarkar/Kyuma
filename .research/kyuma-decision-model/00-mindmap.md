# Mindmap: best free open-source local decision model for Kyuma (run 2, full protocol)

Decision this informs: which weights to load in Phase 05/06 (model-server + decision-json gates).

## What I think I know (after run 1)

- Task = 8-way intent→JSON on one short sentence, temp 0, grammar-constrained (GBNF/JSON-schema). No reasoning needed. (confidence: high)
- Qwen beats Llama at every small size on function-calling; Llama-3.2 smalls eliminated. (confidence: high — BFCL V4 + 3 indie roundups converge)
- GBNF makes JSON validity infrastructure, not model choice. (confidence: high — JSONSchemaBench + llama.cpp docs)
- Bake-off: Qwen3-0.6B (default) vs Qwen2.5-1.5B-Instruct. (confidence: med — ordering on OUR intents unproven)

## What I don't know (gaps for run 2)

- [G5] Do papers back sub-2B edge function-calling with voice input? → hunt: OpenAlex + arXiv.
- [G6] Does grammar-aware fine-tuning on a 1.5B change the fallback story? → hunt: web for intent→JSON SFT results.
- [G7] Qwen3 thinking mode: exact mechanism to disable for deterministic low-latency calls? → hunt: official Qwen3 docs/cards.
- [G8] Perplexity chatbot cross-check → BLOCKED: no browser extension connected (debug_websocket_status confirmed). Compensated with papers + extra sweeps. Marked UNRESOLVED, low cost to retry when browser is back.

## Hunt plan (run 2)

1. OpenAlex API: "small language model function calling", "constrained decoding JSON schema", "tiny intent classification edge".
2. Web sweeps: grammar-aware fine-tuning small models; Qwen3 GGUF thinking control.
3. Mirror EVERYTHING (mindmap, all source logs, FINAL) to vault Research/Kyuma-decision-model/.
