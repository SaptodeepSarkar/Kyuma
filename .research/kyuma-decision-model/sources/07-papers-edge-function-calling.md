# Source: TinyAgent + in-vehicle SLM + DispatchQA papers (via OpenAlex)

- Via: OpenAlex API `api.openalex.org/works?search=small language model function calling tool use` | Accessed: 2026-10-13
- Types: preprints (arXiv 2409.00608, 2501.02342) + EMNLP Industry 2025 paper.

## What it says

- TinyAgent (Erdogan et al. 2024): task-specific 1.1B model for function calling at the edge, voice/text-driven local Siri-like MacBook assistant — near-identical to Kyuma. Claims parity with GPT-4-Turbo on its tasks via curated data + SFT + tool retrieval + quantization. Dataset, models, package open-sourced.
- In-vehicle SLM (Khiabani et al. 2025): Phi-3-mini pruned/quantized for embedded function-calling control, 11 tok/s WITHOUT hardware acceleration — realtime on-device feasible.
- DispatchQA (Daiber et al., EMNLP 2025): benchmark for small-model query→API-call; fine-tuned Llama-3.1-8B matches/beats GPT-4o at 3x speed. All data/code/checkpoints public.

## What I take from it

- G5: peer-reviewed + preprint evidence that ~1B + SFT + quant = GPT-4-class on narrow function-calling, including voice-driven assistants. Kyuma's 1B plan is on solid ground.
- Method template for our fallback: curated data + SFT + short tool list (retrieval) + quant.

## Trust

- Evidence: experiments with open artifacts (TinyAgent, DispatchQA) | Limitations: task-specific numbers don't transfer 1:1 to our 8 intents; TinyAgent uncited.
- Confidence: med-high for direction, med for numbers.
