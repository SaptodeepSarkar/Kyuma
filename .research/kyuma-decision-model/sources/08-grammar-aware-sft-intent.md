# Source: grammar-aware SFT for intent→JSON (featherless 1.5B weather-intent) + constrained-decoding caveats

- URLs: https://featherless.ai/models/Nicholas55555/qwen2.5-1.5b-weather-intent-v2-merged , https://marovi.ai/Constrained_Decoding | Accessed: 2026-10-13 | Via: websearch "grammar-aware fine-tuning small language models constrained decoding"
- Type: community model report + technical explainer.

## What it says

- Qwen2.5-1.5B + LoRA intent-parsing finetune: in-scope slot exact-match 52% → 100%, out-of-scope recall 80% → 100%, false-accept 0%, false-reject 0%, OOV errors 30 → 0. This is Kyuma's exact task shape (short query → structured JSON intent + must-reject-gibberish).
- Marovi: hard constraints cause distribution shift — forcing legal tokens can yield plausible-but-wrong content when the model disagrees; mitigation is exactly instruction-tuning on schema-conformant data (i.e. grammar-aware SFT). Production pattern: finetune + constrained decoding together.
- Counter-note (ResearchGate "Let Me Speak Freely" study): constrained decoding can degrade reasoning performance; for classification-shaped tasks JSON formatting sometimes helps. Kyuma is classification-shaped — favorable.

## What I take from it

- G6: fallback ladder upgraded — grammar-aware SFT on 1.5B is proven at 100%/100% on intent→JSON with OOS rejection. If Phase 06 bake-off fails, finetune; don't scale up.
- Reinforces Phase 06 gibberish→noop gate (FAR must be 0).

## Trust

- Evidence: single-task community report (unverified here) + well-argued explainer citing PICARD/Synchromesh lineage.
- Confidence: med — numbers are task-specific, but the SFT+GBNF pattern is corroborated by TinyAgent/sagnik too.
