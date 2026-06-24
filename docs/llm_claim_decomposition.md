# Rule-Guided LLM Claim Decomposition

The project keeps the deterministic rule-based requirement decomposer as a baseline, fallback, and diagnostic source. The automatic prediction pipeline can additionally use `rule_guided_llm`, where the rule output is passed to an LLM as structured guidance and the LLM output becomes the final predicted claim decomposition.

There is no human review step in this path. Gold claims remain offline evaluation data only; LLM output is prediction data, not gold data.

## Strategy

`rule_guided_llm` runs the existing rule-based decomposer first, then sends the LLM:

- original requirement text
- cleaned requirement text
- rule-based claims
- deterministic quality flags
- detected textual patterns

The prompt asks for JSON only and uses prompt version `CLAIM_DECOMPOSITION_RULE_GUIDED_V2`. Returned claims are validated against the structured schema with `claim_kind`, `ui_evaluability`, `importance`, and optional rationale.

If the LLM response cannot be parsed, the decomposer retries once with a repair prompt. With `strict=True`, LLM errors raise. With `strict=False`, the component falls back to the rule-based claims and records flags such as `LLM_UNAVAILABLE`, `LLM_PARSE_ERROR`, or `LLM_SCHEMA_INVALID`.

## API

The legacy API remains deterministic and requires no API key:

```python
decompose_requirement(text: str) -> list[str]
```

The richer API returns diagnostics and structured claims:

```python
decompose_requirement_with_diagnostics(
    text,
    strategy="rule_guided_llm",
)
```

Use `strategy="rule_based"` for deterministic output with the same result shape.

## CLI

The external evaluator defaults to the deterministic rule-based decomposer. To use the automatic rule-guided LLM strategy:

```bash
PYTHONPATH=src python scripts/evaluate_claim_decomposition_external.py \
  --input data/annotations/requirements_candidate \
  --out data/generated/claim_decomposition_checks/project_rule_guided_llm_decomp.json \
  --claim-decomposer rule_guided_llm \
  --limit 100
```

Optional flags:

- `--llm-provider {gemini,deepseek}`
- `--llm-model MODEL_NAME`
- `--no-cache`
- `--strict-llm`

The default LLM role is `claim_decomposition`, configured in `configs/models.json`
and currently set to provider `gemini`, model `gemini-2.5-flash-lite`, temperature `0.0`. You can override
it for an evaluation run with `UI_VERIFIER_CLAIM_DECOMPOSITION_PROVIDER`,
`UI_VERIFIER_CLAIM_DECOMPOSITION_MODEL`, and
`UI_VERIFIER_CLAIM_DECOMPOSITION_TEMPERATURE`, or pass `--llm-provider` and `--llm-model` explicitly.

DeepSeek example for a cheap text-only ablation:

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

## Provider Setup

Gemini calls read `GEMINI_API_KEY`. DeepSeek calls read `DEEPSEEK_API_KEY` and optionally `DEEPSEEK_BASE_URL`. Do not commit `.env` files or hard-code keys.

Rule-based decomposition and unit tests do not require provider API keys.

## Caching

LLM responses are cached under:

```text
data/generated/cache/claim_decomposition_llm/
```

The cache key includes the prompt version, model name, normalized original text, rule-based claim hash, quality flag hash, and detected pattern hash. Cache files store the raw response, parsed result, prompt metadata, rule output, diagnostics, and timestamp.

## Limitations

The LLM receives only requirement text and rule-decomposer diagnostics. It must not add screenshot evidence or decide final verification labels. Hidden, backend, policy, legal, security, database, architecture, performance, and license constraints are preserved as claims but marked as non-UI or hidden system behavior when appropriate.
