# Model Configuration

The project uses role-based provider/model defaults so experiments can change model choices without editing code. The active defaults live in:

```text
configs/models.json
```

At runtime, `ui_verifier.model_config` resolves each role from three layers:

1. Built-in defaults in code.
2. `configs/models.json`, or another JSON file set with `UI_VERIFIER_MODEL_CONFIG`.
3. Role-specific environment variables.

The backend exposes the resolved configuration at:

```text
GET http://127.0.0.1:8000/model-config
```

## Roles

| Role | Default provider | Default model | Default temperature | Use |
|---|---:|---:|---:|---|
| `claim_decomposition` | `gemini` | `gemini-2.5-flash-lite` | `0.0` | Rule-guided text-only claim decomposition. |
| `pipeline_claim_fallback` | `deepseek` | `deepseek-chat` | `0.0` | Cheap text-only LLM fallback when heuristic pipeline decomposition is weak. |
| `evidence_retrieval` | `deepseek` | `deepseek-chat` | `0.0` | Text-only LLM reranking over extracted screen text/OCR/summaries. |
| `verification` | `gemini` | `gemini-2.5-flash` | `0.2` | Screenshot-grounded verification. |
| `demo_image_verifier` | `gemini` | `gemini-2.5-flash-lite` | `0.0` | Budget-capped demo image verifier. |
| `requirement_harvest` | `gemini` | `gemini-2.5-flash` | `0.0` | CLI flow-level requirement harvesting. |
| `api_requirement_harvest` | `gemini` | `gemini-2.5-flash` | `0.7` | Interactive API harvesting, preserving the previous exploratory default. |
| `candidate_rewrite` | `gemini` | `gemini-2.5-flash-lite` | `0.0` | Text-only candidate normalization. |
| `claim_rephrase` | `gemini` | `gemini-2.5-flash-lite` | `0.1` | Single-claim reviewer-assisted rewrite. |
| `screen_description` | `gemini` | `gemini-2.5-flash` | `0.2` | Ad-hoc multimodal screen descriptions. |
| `contrastive_generation` | `external` | `user-provided-model` | `0.2` | Manual/external contrastive generation provenance label. |

## Override Examples

Use another config file for an evaluation run:

```bash
UI_VERIFIER_MODEL_CONFIG=configs/models_eval_stronger.json \
PYTHONPATH=src python scripts/run_verification_pipeline.py \
  --flow-dir data/processed/flows/mind2web/03_mbta_c094948f-afc6-415c-968a-9e105e2db118 \
  --requirements data/annotations/requirements_gold/03_mbta_c094948f-afc6-415c-968a-9e105e2db118/gold_requirements.json \
  --out data/generated/eval_runs/03_mbta.json
```

Override one role without creating a file:

```bash
UI_VERIFIER_CLAIM_DECOMPOSITION_PROVIDER=gemini \
UI_VERIFIER_CLAIM_DECOMPOSITION_MODEL=gemini-2.5-flash \
UI_VERIFIER_CLAIM_DECOMPOSITION_TEMPERATURE=0.0 \
PYTHONPATH=src python scripts/evaluate_claim_decomposition_external.py \
  --input data/raw/pure \
  --source-kind pure \
  --claim-decomposer rule_guided_llm \
  --out data/generated/claim_decomposition_checks/pure_flash.json
```

Role environment variable names are formed as:

```text
UI_VERIFIER_<ROLE>_PROVIDER
UI_VERIFIER_<ROLE>_MODEL
UI_VERIFIER_<ROLE>_TEMPERATURE
```

For example, `pipeline_claim_fallback` becomes `UI_VERIFIER_PIPELINE_CLAIM_FALLBACK_MODEL`.

## Model Choice Guidance

Use `deepseek-chat` for cheap text-only pipeline steps when image input is not required: pipeline claim fallback and text-only evidence reranking. Use low temperature for stable JSON evaluation output.

Use `gemini-2.5-flash-lite` for cheap multimodal claim verification when screenshots are attached. DeepSeek is not used for screenshot verification in this code path because the DeepSeek client is text-only.

Use `gemini-2.5-flash` for multimodal or high-recall steps: screenshot verification, screen descriptions, and requirement harvesting from multiple screenshots. These tasks are more sensitive to missed visual details.

For evaluation, record the resolved role config together with run metadata. Existing pipeline outputs already store selected model names for the claim fallback and verifier; `/model-config` gives the full resolved configuration for reports.

## DeepSeek Text-Only Ablation

DeepSeek is wired for text-only JSON tasks through the OpenAI-compatible `/chat/completions` API. Use it for claim decomposition experiments and text-only evidence reranking, not screenshot verification. The client reads `DEEPSEEK_API_KEY` and optionally `DEEPSEEK_BASE_URL`.

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key_here \
PYTHONPATH=src python scripts/evaluate_claim_decomposition_external.py \
  --input data/raw/pure \
  --source-kind pure \
  --claim-decomposer rule_guided_llm \
  --llm-provider deepseek \
  --llm-model deepseek-v4-flash \
  --out data/generated/claim_decomposition_checks/pure_deepseek_v4_flash.json
```

For pipeline fallback ablations:

```bash
DEEPSEEK_API_KEY=your_deepseek_api_key_here \
PYTHONPATH=src python scripts/run_verification_pipeline.py \
  --flow-dir data/processed/flows/mind2web/03_mbta_c094948f-afc6-415c-968a-9e105e2db118 \
  --requirements data/annotations/requirements_gold/03_mbta_c094948f-afc6-415c-968a-9e105e2db118/gold_requirements.json \
  --out data/generated/eval_runs/03_mbta_deepseek_claims.json \
  --claim-provider deepseek \
  --claim-model deepseek-v4-flash
```

Keep Gemini for roles that pass screenshots, because those call paths require media input.
