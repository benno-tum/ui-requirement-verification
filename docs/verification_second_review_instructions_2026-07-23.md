# Independent Verification-Label Second Review

The prepared review form contains 44 blinded requirements from all 13
Mind2Web-derived flows:

- all eight rare `NOT_FULFILLED` items;
- twelve items from each of the other three primary-label strata;
- at least one item from every flow.

The reviewer receives requirement text, the complete ordered screenshot list,
the four label definitions, and blank response fields. The form intentionally
contains neither the primary author's label nor any model prediction.

Generate or refresh the form:

```bash
python scripts/build_verification_second_review_sample.py
```

Share only:

`data/annotations/evaluation_audits/verification_label_second_review_20260723/second_review_form.json`

The reviewer fills:

- `reviewer.reviewer_id`;
- `reviewer_started_at` and `reviewer_completed_at`;
- `reviewer_label`;
- `reviewer_evidence_steps`;
- `reviewer_confidence`;
- `reviewer_notes`.

After every item is complete, evaluate agreement and create the adjudication
queue:

```bash
python scripts/evaluate_verification_second_review.py \
  data/annotations/evaluation_audits/verification_label_second_review_20260723/second_review_form.json
```

Report raw agreement, Cohen's kappa, the complete confusion matrix, class-level
agreement, and the adjudication process. Because the sample deliberately
oversamples rare labels, do not present its raw agreement as a
prevalence-weighted estimate for all 258 benchmark items.

No disagreement changes gold automatically. A human adjudicator must fill the
generated queue and document the final decision.
