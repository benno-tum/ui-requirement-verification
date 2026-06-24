# Meeting Summary: Verification Pipeline

**Date:** 24 June 2026

## Current State

The evidence-first verification pipeline is runnable end to end from the command line. It takes textual requirements and an ordered screenshot flow, retrieves relevant screenshots, verifies visible evidence, and writes structured JSON containing:

- a final label (`FULFILLED`, `PARTIALLY_FULFILLED`, `NOT_FULFILLED`, or `ABSTAIN`)
- claim-level decisions and rationales
- selected evidence screenshots
- UI-evaluability and uncertainty information
- model, cache, retry, and execution metadata

The current setup uses DeepSeek for text-only claim decomposition and evidence retrieval, and Gemini Flash Lite for screenshot verification. Independent verification calls can run in parallel through `--claim-workers`.

## Configuration and Ablations

The main stages are configurable without changing code:

- Claim decomposition: enabled by default; disable with `--no-claims`
- LLM claim fallback: disable with `--no-llm-claim-fallback`
- Evidence retrieval: `lexical`, `tfidf`, `embedding`, or `llm`
- Number of retrieved screenshots: `--top-k`
- Verification: deterministic baseline or Gemini image verifier
- Parallelism: `--claim-workers`
- API budget, retries, models, providers, and cache paths

With `--no-claims`, each complete requirement is treated as one verification unit. This preserves the output format and enables a direct comparison between claim-based and requirement-level verification.

## Preliminary Results

The first reviewed flows exposed two implementation issues: a hidden-property detector incorrectly interpreted the word "store" as "stored", and temporary Gemini availability errors were not retried. The detector was corrected and regression-tested, and runs now support configurable retries.

The MBTA flow completed successfully with no model failures or fallbacks. It processed 24 requirements in approximately 155 seconds, used 9 new Gemini calls and 32 cached results, and matched 16 of 24 current reviewed labels. The eight disagreements are the next cases for qualitative error analysis.

These numbers are preliminary. Several gold files still have `needs_review` status, so they should not yet be presented as final benchmark performance.

## Reproducible Run

Example with claims and four parallel verification workers:

```bash
/usr/bin/time -p env PYTHONPATH=src python scripts/run_verification_pipeline.py \
  --flow-dir data/processed/flows/mind2web/04_underarmour_18fc60d7-aa69-4c07-9bf1-64543eae52c9 \
  --requirements data/annotations/verification_gold/04_underarmour_18fc60d7-aa69-4c07-9bf1-64543eae52c9/verification_gold.json \
  --requirements-source benchmark \
  --out data/generated/ui_verification_runs/04_underarmour_claims.json \
  --retriever llm \
  --top-k 4 \
  --claim-provider deepseek \
  --claim-model deepseek-chat \
  --retriever-provider deepseek \
  --retriever-model deepseek-chat \
  --verifier gemini-image \
  --verifier-model gemini-2.5-flash-lite \
  --gemini-max-retries 2 \
  --max-verifier-images 4 \
  --max-gemini-api-calls 24 \
  --claim-workers 4
```

For the no-claims ablation, add `--no-claims` and use a separate output and verifier-cache path:

```text
--no-claims
--out data/generated/ui_verification_runs/04_underarmour_no_claims.json
--verifier-cache data/generated/verification_pipeline_cache/04_underarmour_no_claims.json
```

## Next Steps

1. Continue reviewing additional screenshot flows and complete the corresponding gold labels.
2. Run and compare the configurable pipeline variants, especially claim-based and no-claims verification.
3. Investigate disagreements and improve claim decomposition, evidence selection, and final-label aggregation where necessary.
4. Consolidate the evaluation results, including label agreement, abstention behavior, runtime, and API usage.
5. As the final extension, add bounding boxes so that evidence identifies the relevant UI region within each selected screenshot, rather than only the screenshot step.
