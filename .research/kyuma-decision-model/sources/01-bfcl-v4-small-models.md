# Source: BFCL V4 leaderboard mirrors (BenchmarkList / ModelCap / BenchLeader)

- URLs: https://benchmarklist.com/benchmarks/bfcl/ , https://modelcap.ai/benchmarks/bfcl , https://www.benchleader.com/benchmarks/bfcl_overall | Accessed: 2026-10-13 | Via: websearch "Berkeley Function Calling Leaderboard small models Qwen Llama 1B 3B scores 2026"
- Type: leaderboard mirror | Authors: mirror of ShishirPatil/gorilla BFCL V4 (eval commit f7cf735, updated 2026-04-12)

## What it says

- Small-model Overall accuracy: Qwen3-1.7B (FC) 28.41%, Qwen3-0.6B (FC) 23.93%, Llama-3.2-3B (FC) 21.95%, Llama-3.2-1B (FC) 10.82%, xLAM-2-1b-fc-r 30.44%, Hammer2.1-3b 29.71%.
- Non-Live AST sub-split (closer to Kyuma's single-turn task): Qwen3-1.7B 82.92%, Qwen3-0.6B 71.79%, Llama-3.2-3B 82.67%, Llama-3.2-1B 38.38%.
- Qwen3 family leads every size class on FC; Llama-3.2-1B is the weakest measured small model.

## What I take from it

- G1: Qwen > Llama at every comparable size; Llama-3.2-1B eliminated.
- G4: xLAM-2/Hammer are tool-finetune specialists to watch, but check licenses.

## Trust

- Evidence: standardized benchmark, 100+ models, public responses | Limitations: Overall mixes in agentic multi-turn/web-search splits irrelevant to Kyuma; mirrors, not the official board.
- Confidence: high for rank-order, med for absolute numbers on our task.
