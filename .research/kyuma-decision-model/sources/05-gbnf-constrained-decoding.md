# Source: JSONSchemaBench paper + llama.cpp GBNF docs + practitioner guides

- URLs: https://arxiv.org/html/2501.10868v1 , https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md , https://www.gmicloud.ai/en/blog/structured-output-for-llm-inference-json-schema-enforcement-constrained-decoding-and-parse-failure-rates , https://www.aimastery.page/guides/llama-cpp-gbnf-pydantic-guaranteed-json | Accessed: 2026-10-13 | Via: websearch "llama.cpp GBNF grammar constrained JSON output reliability 100% schema compliance"
- Type: peer-reviewed-style benchmark + official docs + practitioner guides.

## What it says

- Constrained decoding makes invalid output unsampleable at token level: parse failure → 0 by construction; also speeds generation up to ~50% (JSONSchemaBench).
- llama.cpp converts JSON Schema → GBNF per request (`response_format`); known limits: no conditionals if/then/else, broken nested $refs, numbers min/max integer-only, unsupported keywords skipped silently.
- Critical caveats (all sources agree): grammar guarantees SYNTAX, not semantics — wrong-but-valid JSON is the new failure mode; schema is invisible to the model → describe fields in system prompt; keep schemas small; validate anyway (Pydantic second gate); small models may stall under additionalProperties:false.

## What I take from it

- G3: YES — with GBNF, model choice shifts from "who emits valid JSON" to "who picks the right intent + args". This downgrades Llama-1B's weakness slightly but mostly rewards the most intent-accurate small model, and makes Phase 06's test_all_intents (not test_schema_valid) the binding gate.
- Design rules for Phase 05/06: tiny flat Exec schema, enum action, required fields, prompt mirrors schema, Pydantic validate + retry.

## Trust

- Evidence: 10K-schema benchmark + official docs + converging practitioner reports.
- Confidence: high.
