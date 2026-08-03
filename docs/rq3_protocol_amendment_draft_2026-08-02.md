# Draft Amendment to the Frozen RQ3 Coding Protocol

Status: awaiting author approval. This document does not modify the protocol frozen on 23 July 2026.

## Why an amendment is necessary

The frozen eligibility rule deliberately includes all model abstentions, label-correct predictions with no reviewed-evidence overlap, and unstable predictions. The original seven primary categories, however, are all framed as failure causes. They therefore cannot validly code three observed row types:

1. Gold and prediction are both `ABSTAIN` (153 rows). Calling these `EXCESSIVE_ABSTENTION` would turn appropriate uncertainty handling into an error.
2. The label is correct but the cited evidence does not overlap the reviewed evidence (97 AI-drafted rows after gold-review candidates are separated). Calling these label errors would conflate decision quality with traceability quality.
3. The current prediction matches gold but repeated runs disagree (2 rows after trace failures are separated). None of the original categories denotes instability without a current label error.

The automatic overlap trigger is especially misleading for correct abstentions. An abstaining model may appropriately provide no positive evidence steps, while the reference evidence records screenshots that demonstrate the absence of a defensible observable outcome. Zero overlap must therefore not automatically be interpreted as a traceability failure for `ABSTAIN`/`ABSTAIN` rows.

## Proposed additional primary outcomes

- `APPROPRIATE_ABSTENTION`: prediction and reference both abstain. This is explicitly a non-error outcome and allows RQ3 to describe which requirement patterns appropriately induce uncertainty.
- `TRACEABILITY_FAILURE`: the requirement label is correct, but the cited evidence has no overlap with the reviewed evidence. This is reported separately from label accuracy.
- `PREDICTION_INSTABILITY`: the current prediction is correct, but repeated runs disagree on the same stored input.

The proposed evidence tag `RUN_INSTABILITY` records instability on rows whose primary category remains a more specific current-run error, such as an evidence-selection miss.

## Reporting rule

Final error-category percentages must exclude `APPROPRIATE_ABSTENTION` from the error denominator. `GOLD_REVIEW_CANDIDATE` rows must be resolved before attribution to a model-error category. Counts remain condition–item observations; they are not 653 independent benchmark requirements.

## Approval decision

Before final analysis, the author should choose one of the following and record the decision:

- Approve the amendment and retain the three added outcome categories.
- Reject it and revise the eligibility rule so correct abstentions and current-correct unstable rows are analyzed in separate, non-error summaries rather than forced into the original category taxonomy.

Either option is defensible if applied consistently and documented before reporting the completed coding results.
