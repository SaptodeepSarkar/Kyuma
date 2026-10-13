# Source: sagnik3788/Qwen2.5-1.5B-Instruct-FC model card (Hugging Face)

- URL: https://huggingface.co/sagnik3788/Qwen2.5-1.5B-Instruct-FC | Accessed: 2026-10-13 | Via: websearch "Qwen2.5-1.5B-Instruct vs Llama-3.2-1B function calling JSON accuracy benchmark"
- Type: model card (community finetune) | Method: QLoRA SFT r16, 10k verified synthetic FC examples, 3 epochs.

## What it says

- Claims 85.65% BFCL v4 Non-Live AST at 1.5B, "beating 71/109 models incl. 72B/685B giants"; Live 73.58%; multi-turn/memory/web-search splits 0% (not trained).
- Baseline quoted: Llama-3.2-1B 38.38% (matches BFCL mirror NL-AST number above).
- Usage: `apply_chat_template(tools=...)` → `<tool_call>JSON</tool_call>`.

## What I take from it

- G1: a 1.5B CAN reach 85%+ single-turn FC accuracy with targeted SFT — sets the ceiling and gives us a fallback artifact.
- G4: third-party weights = maintenance/trust risk vs official Qwen drops.

## Trust

- Evidence: self-reported eval, method documented (APIGen 3-stage pipeline) but not independently reproduced here.
- Confidence: med — direction (SFT helps enormously at 1.5B) high, exact 85.65 low until Phase 06 reproduces on our fixture.
