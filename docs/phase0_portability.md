# Phase 0 portability and provenance

The pinned upstream tree is kept intact. These compatibility layers are deliberately outside the official implementation.

| Upstream issue | Stage 1 handling | Provenance preserved |
|---|---|---|
| Game24 dataset is referenced but not shipped | `selective_context.portability.game24_dataset` builds the expected lightweight JSONL from a caller-provided source; downloading is never implicit | Dataset source and revision are required metadata |
| `aggregate_data_minimal.py` is referenced but absent | `selective_context.portability.aggregate_minimal` delegates to the shipped `data_generation.aggregate_data` CLI | No aggregation logic fork |
| Evaluator requires a dataset-root flag that general-inference scripts omit | `selective_context.portability.game24_eval` evaluates generated records through the shipped Game24 verifier without inventing a fake dataset path | Official correctness function is called directly |
| TED analysis contains machine-specific absolute paths | New audit code takes all paths as CLI arguments | Official TED code is unmodified |
| vLLM cannot be installed for the Windows CPU smoke test | Official `utils/general_inference/vllm_serving.py` remains the reproduction backend; the new HF eager backend is isolated in `selective_context/` | Server dependency file keeps the official inference pins |
| Local Python is 3.9 while upstream `math-verify==0.8.0` requires Python >=3.10 | The round-trip test first imports the official evaluator and otherwise uses a narrowly scoped Game24-only arithmetic fallback; Stage 2 must use the official dependency stack | Output keys and boxed-answer behavior are unchanged; server parity remains a mandatory gate |

Prompt sources are frozen to the official JSON templates:

- R0: `prompt_templates/init_response_prompt_templates.json:qwen_math_prompt`
- R1: `prompt_templates/1f_templates.json:1f`
- R2–R4: `prompt_templates/prompted_error_signal_templates.json:new_prompted_error_signal_1f`

The expression audit can call the official TED parser when its optional dependencies are present. The stepwise audit is separate because the upstream TED pipeline parses a final extracted expression tree, not a natural-language step dependency graph.
