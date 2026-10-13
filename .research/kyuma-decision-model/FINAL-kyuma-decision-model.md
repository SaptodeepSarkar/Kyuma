# FINAL: Kyuma decision model — speed vs accuracy (run 2, full protocol)

Project copy of this file: /home/saptodeep/Projects/Kyuma/.research/kyuma-decision-model/FINAL-kyuma-decision-model.md
Mindmap: 00-mindmap.md in this folder. Source logs: sources/01–09 in this folder.

## Answer first (5-line verdict)

1. **Bake off two models in Phase 06; default to Qwen3-0.6B** (official GGUF, Q4_K_M, resident llama.cpp ≥ b5401, temp 0, GBNF grammar, thinking hard-OFF via enable_thinking=False).
2. Qwen beats Llama at every small size (BFCL V4: Qwen3-0.6B 23.9 / Qwen3-1.7B 28.4 / Llama-3.2-1B 10.8); **all Llama-3.2 smalls eliminated**. Papers back the plan: TinyAgent (1.1B voice-driven edge assistant ≈ Kyuma) matches GPT-4-Turbo on its tasks.
3. GBNF makes JSON validity **solved infrastructure** (parse failures zero by construction) — the bake-off tests intent accuracy, not syntax. Caveat: hard constraints can force plausible-but-wrong content; mitigation is grammar-aware SFT + Pydantic second gate.
4. Strongest new evidence: grammar-aware SFT on Qwen2.5-1.5B for intent→JSON hit **100% in-scope exact-match (from 52%), 100% out-of-scope recall, 0% false-accept** — so the fallback is finetune, never scale up.
5. 1.5B-class speed evidence: 92% Top-1 tool selection at ~94ms p50 on GPU; short decision JSON clears the 500ms gate with margin. GPU mandatory (CPU 8–16x slower).

## Mindmap recap

Run 1 believed the sourceless Qwen2.5-1.5B pick and confirmed the family but not the size. Run 2 changed two things: (a) Qwen3-0.6B became the default (official GGUF, 84%-class head-to-head, half the VRAM); (b) papers + SFT reports turned the fallback from "bigger model" into "finetune the 1.5B". G8 (Perplexity cross-check) is UNRESOLVED — no browser extension connected; retry cost is low.

## Findings by gap

- **G1 accuracy**: BFCL V4 smalls per sources/01; ceiling proof 85.65 NL-AST via 1.5B SFT per sources/02 (med confidence, self-reported); 92% Top-1 @94ms per sources/03.
- **G2 speed**: 1.5B Q4_K_M ~1GB, ~21–38 tok/s consumer GPU; 0.6B ~2x faster; GPU mandatory per sources/03+04.
- **G3 JSON-reliability**: GBNF guarantees syntax (JSONSchemaBench, llama.cpp docs, sources/05); distribution-shift caveat + SFT mitigation per sources/08. Schema design rules: flat, enum action, required fields, no conditionals/nested-$refs, prompt mirrors schema, Pydantic validates.
- **G4 contenders**: shortlist Qwen3-0.6B / Qwen2.5-1.5B-Instruct / sagnik-FC-1.5B; eliminated Llama smalls, xLAM-2 (license), 0.5B class, 3B+, Mistral 7B (sources/06).
- **G5 papers**: TinyAgent 1.1B edge voice assistant, Phi-3-mini in-vehicle at 11 tok/s CPU-free, DispatchQA fine-tuned SLM ≈ GPT-4o at 3x speed (sources/07).
- **G6 SFT fallback**: 1.5B intent→JSON 100%/100%/0%-FAR after grammar-aware LoRA (sources/08).
- **G7 thinking control**: OFF by default-needed; hard switch enable_thinking=False; -2507 weights non-thinking-only; temp 0 for us (not vendor 0.7); presence_penalty 1.5 for quants (sources/09).
- **G8 Perplexity**: UNRESOLVED (no extension connection).

## Source table

| # | Source | Found via | Contributed |
|---|---|---|---|
| 01 | BFCL V4 mirrors | websearch BFCL small-model scores | rank-order + NL-AST, Llama elimination |
| 02 | sagnik Qwen2.5-1.5B-FC card (HF) | websearch Qwen2.5 vs Llama FC | SFT ceiling claim, fallback artifact |
| 03 | jishuzhan latency study | websearch Qwen3-0.6B vs Qwen2.5-1.5B | 92% @94ms, GPU-mandatory, stuffing failure mode |
| 04 | Qwen official + llamaperf/community | websearch llama.cpp 1.5B tok/s | VRAM fit + gate math |
| 05 | JSONSchemaBench + llama.cpp GBNF docs + guides | websearch GBNF reliability | syntax-solved, schema rules |
| 06 | vdf.ai / graysoft / heyneo / obakavv | all sweeps | 0.6B 84%-class evidence, licenses, shortlist |
| 07 | TinyAgent / in-vehicle SLM / DispatchQA | OpenAlex API "small language model function calling" | paper backing for ~1B edge voice FC |
| 08 | featherless 1.5B intent SFT + Marovi explainer | websearch grammar-aware fine-tuning | 100%/100% SFT fallback, shift caveat |
| 09 | Qwen3 GGUF cards + qwen3 repo + blog | websearch Qwen3 GGUF thinking control | official GGUFs, thinking-off mechanism |

## How this helps (next actions)

1. Phase 05: `llama-server -hf Qwen/Qwen3-0.6B-GGUF:Q4_K_M`, Jinja chat template with enable_thinking=False, `response_format: json_schema` per request; log VRAM with Vosk alongside.
2. Phase 06: bake-off vs Qwen2.5-1.5B-Instruct on the 40-sentence fixture; gibberish→noop gate guards FAR (target 0).
3. If bake-off fails: grammar-aware LoRA on 1.5B with ~200 boundary examples (sources/03 ROI + sources/08 recipe), NOT a bigger model.

## Evidence holds?

- Strong: Qwen-small > Llama-small (4+ sources); GBNF syntax guarantee (benchmark + docs); GPU-mandatory (measured); thinking-off mechanism (official docs).
- Medium: tok/s absolutes (±20%); sagnik 85.65 + featherless 100% (single-source, task-specific); TinyAgent numbers (uncited preprint).
- Weak: willitrun estimates (bounds only). G8 unresolved.

## Significance / open

Model risk is bounded three deep: 0.6B default → 1.5B challenger → proven SFT recipe. Still open: (a) fixture bake-off result; (b) Vosk coexistence VRAM on the actual GPU. Next hunt only if SFT path is taken: QLoRA recipes for Qwen3-0.6B tool-calling (Axolotl/Unsloth configs).

## Sources

Full URLs + access dates + query strings: see sources/01–09 in this folder. All accessed 2026-10-13.

Checked 2026-10-13.
