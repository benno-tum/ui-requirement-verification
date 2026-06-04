# Verification Metrics

Use `scripts/evaluate_verification_metrics.py` to evaluate verifier outputs against the human `verification_gold` annotations.

## Supported Prediction Formats

The evaluator accepts either one JSON file or a directory of JSON files. It supports:

- `VerificationRun` outputs with `verdicts`, e.g. `data/generated/verification_runs/<flow_id>/verification_run.json`
- evidence-first pipeline outputs with `results`, e.g. `data/generated/verification_pipeline/<flow_id>.json`
- demo verification outputs with the same `results` structure

## Command

```bash
python scripts/evaluate_verification_metrics.py \
  --predictions data/generated/verification_pipeline \
  --out data/generated/evaluation/verification_pipeline_metrics.json \
  --k 1 \
  --k 3
```

For Gemini verification runs saved under `data/generated/verification_runs`:

```bash
python scripts/evaluate_verification_metrics.py \
  --predictions data/generated/verification_runs \
  --out data/generated/evaluation/gemini_verification_metrics.json \
  --k 1 \
  --k 3
```

## Metrics

Label metrics compare `verification_label` from gold against predicted `label` or `final_label`:

- `accuracy`
- `macro_f1`
- `weighted_f1`
- per-class precision / recall / F1 / support
- confusion matrix
- `abstain_rate`
- `false_fulfillment_rate`
- prediction coverage

Evidence metrics compare predicted evidence steps against gold evidence steps:

- `precision_at_k`
- `recall_at_k`
- `hit_at_k`
- `mrr`

Claim-status metrics are computed when prediction outputs contain claims. Gold and predicted claims are greedily matched by token-F1 similarity, then statuses are compared:

- claim-status macro F1
- claim confusion matrix
- claim match recall

## Interpretation

Use `macro_f1` as the main end-to-end metric because the four verification labels are imbalanced. Use `false_fulfillment_rate` as the safety metric for the evidence-first policy: it measures how often the system predicts `FULFILLED` when gold is not `FULFILLED`.

Missing predictions are counted as `ABSTAIN` and also reported via prediction coverage. This makes partial runs conservative while keeping the missing-output problem visible.
