# Systematic Error Analysis and Review Plan

Date: 2026-07-02

## Status Check

There was no single systematic error-analysis artifact across all current flows yet.
Existing material covered parts of it:

- `docs/accuracy_analysis_2026-06-25.md` contains a useful flow-level accuracy report and qualitative notes.
- `docs/claim_review_workflow.md` defines how to review `verification_gold` safely.
- `data/generated/evaluation_review/...` contains detailed MBTA-only review artifacts.

This document combines the current cross-flow numbers with a concrete review process.

## Current Run Set

The analysis uses the latest local UI verification runs for flows 01-13, matched against `data/annotations/verification_gold`.

Compared items: **258**

Label matches: **173 / 258 = 67.1%**

Gold labels:

- `FULFILLED`: 159
- `PARTIALLY_FULFILLED`: 56
- `ABSTAIN`: 31
- `NOT_FULFILLED`: 12

Predicted labels:

- `FULFILLED`: 171
- `PARTIALLY_FULFILLED`: 51
- `ABSTAIN`: 33
- `NOT_FULFILLED`: 3

The model still predicts `FULFILLED` more often than the gold benchmark. This is the clearest systematic bias.

## Error Categories

### 1. Over-fulfillment bias

Count: **35**

Pattern: the model predicts `FULFILLED`, but gold is `PARTIALLY_FULFILLED`, `ABSTAIN`, or `NOT_FULFILLED`.

Interpretation: this is mostly model bias. The model often treats visible partial evidence as complete fulfillment, especially for universal, hidden, or future-state requirements.

Representative cases:

- Flow 06 `CONTR-03`: "every visible department or team area" is treated as fulfilled from one visible path.
- Flow 09 `CONTR-02`: visible format feedback is treated as proof that different lookup failure modes are distinguished.
- Flow 11 `REQ-13`: search controls are treated as proof that correct cruise results are returned.
- Flow 12 `REQ-09`: advanced-search form visibility is treated as proof that filtered results are displayed.

Mitigation:

- Require visible support for every core claim before `FULFILLED`.
- Downgrade to `PARTIALLY_FULFILLED` when only the UI entry point is visible.
- Use `ABSTAIN` for backend correctness, result completeness, active availability, and external side effects.

### 2. Anti-abstain bias

Count: **12**

Pattern: gold is `ABSTAIN`, but the model predicts a concrete label.

Interpretation: this is also mostly model bias. The model prefers making a judgment even when the screenshot flow does not contain enough evidence.

Representative cases:

- Flow 04 `CONTR-03`: future-date restriction and unavailable-date feedback are inferred too strongly.
- Flow 11 `CONTR-03`: completeness of all matching cruises is inferred without a reliable result set.
- Flow 12 `CONTR-03` / `CONTR-04`: catalog correctness and completeness are inferred from partial visible UI.
- Flow 13 `CONTR-03`: currently valid coupon offers are inferred without validating validity.

Mitigation:

- Add an explicit "no visible proof, no concrete label" rule.
- Treat completeness, validity, availability, and future persistence as `ABSTAIN` unless directly visible.

### 3. Under-calling / over-abstaining

Count: **16**

Pattern: gold is positive or partial, but the model predicts `ABSTAIN` or `NOT_FULFILLED`.

Interpretation: this is often pipeline/evidence selection, not pure model intelligence. Many of these cases have no evidence overlap, meaning the relevant screenshot was not selected.

Representative cases:

- Flow 10 `REQ-09`, `REQ-15`, `REQ-16`, `REQ-18`: cart/add-on/final-state evidence exists, but predicted evidence misses late screens.
- Flow 08 `REQ-06`, `REQ-10`: cafe-service information is missed.
- Flow 09 `REQ-09`: balance-lookup partial support is missed.

Mitigation:

- For cart, checkout, review, summary, result, and final-state requirements, force inclusion of late screenshots.
- Add a retrieval rule that includes both the action screen and the resulting state.
- Use bounding boxes later to focus evidence once the correct screenshot is selected.

### 4. Boundary errors

Count: **22**

Pattern: the prediction is neither clearly over-fulfilled nor clearly over-abstained, but the label boundary differs.

Interpretation: this is a mix of model intelligence limits and benchmark strictness. Common boundaries are `FULFILLED` vs. `PARTIALLY_FULFILLED`, and `NOT_FULFILLED` vs. `ABSTAIN`.

Representative cases:

- Flow 10 `REQ-12` / `REQ-13`: cart line-item evidence is partly missed or interpreted too weakly.
- Flow 11 `CONTR-05`: inline search fields are confused with a dedicated review panel.
- Flow 12 `REQ-10` / `REQ-11`: persistent global storefront controls are interpreted too cautiously.

Mitigation:

- Write strict label guidelines with examples.
- During review, decide whether benchmark labels are intentionally strict or whether the gold label should be corrected.

## Evidence / Top-k Findings

Across all 258 items:

- Exact evidence match: **59**
- Partial evidence overlap: **136**
- No evidence overlap: **63**

Among the 173 label-correct cases:

- Exact evidence match: **44**
- Partial overlap: **95**
- No overlap: **34**

Interpretation:

- Top-k usually finds at least some relevant evidence when the label is correct: **139 / 173 = 80.3%** exact or partial overlap.
- But **34 / 173 = 19.7%** label-correct cases still have no evidence overlap. These are traceability problems even when accuracy looks fine.
- The most important evidence-selection failures are late-state flows, especially cart, checkout, review, result, and summary screens.

## Dominant Semantic Patterns

Most label mismatches involve at least one of these requirement types:

- Universal/comparative claims: **85 category hits**
- Late-state cart/checkout claims: **22**
- Result/search-output claims: **22**
- Persistence/cross-step claims: **17**
- Hidden/external behavior: **16**
- Review/summary-state claims: **15**

This suggests that performance improvements should not be generic prompt polishing. They should target these specific requirement types.

## Bias vs. Model Intelligence

Useful framing for the thesis:

- Model bias: systematic preference to mark visible partial evidence as sufficient. This appears in over-fulfillment and anti-abstain cases.
- Model intelligence limit: difficulty with multi-step state, universal quantifiers, comparison, result correctness, and hidden properties.
- Pipeline limitation: relevant screens are sometimes not in top-k, especially late cart/result/review states.

The current results are therefore not only "prompt quality". They expose three separable improvement axes: label policy, evidence retrieval, and reasoning over complex requirements.

## Optimized Review Process

### Review Pass 1: Label mismatches only

Start with the **73 `needs_review` items whose predicted label disagrees with gold**.

Order:

1. Over-fulfilled cases first, because they reveal the main model bias.
2. Gold-`ABSTAIN` cases where the model predicts a concrete label.
3. Under-called cases with no evidence overlap, because these are likely retrieval/top-k issues.
4. Boundary cases, where benchmark strictness may need final adjudication.

For each item, record one short review tag:

- `model_over_fulfilled`
- `model_should_abstain`
- `retrieval_missed_late_state`
- `label_boundary`
- `gold_label_update_candidate`

### Review Pass 2: Label match but evidence mismatch

Then review the **17 `needs_review` items where the label matches but evidence has no overlap**.

Purpose: improve traceability without conflating it with label accuracy.

Typical examples:

- Flow 10 `REQ-06`, `REQ-07`, `REQ-10`, `REQ-11`: add-on detail and quantity screens.
- Flow 05 `REQ-08`, `REQ-09`: dietary profile screens.
- Flow 08 `REQ-07`, `REQ-08`, `REQ-09`: cafe menu resource screens.

### Review Pass 3: Flow-level cleanup

Recommended flow order:

1. Flow 10: strongest late-state/top-k issue.
2. Flow 09: many over-fulfillment and ABSTAIN-boundary issues.
3. Flow 06: strong universal/comparative over-fulfillment pattern.
4. Flows 11, 12, 13: result/search/persistence and hidden-property boundaries.
5. Flows 04, 05, 07, 08: smaller cleanup.

Flows 01-03 are less urgent for final manual review, but flow 01 should remain flagged because older runs had API fallback issues.

## Concrete Improvement Plan

1. Run ablations:
   - full pipeline;
   - no claim decomposition;
   - no top-k, all screenshots;
   - minimal baseline: whole requirement plus all screenshots.
2. Add stricter label policy to the verifier prompt:
   - no `FULFILLED` without all core observable claims;
   - no concrete label for hidden completeness/validity/availability without direct evidence;
   - result correctness requires a visible result state.
3. Improve top-k:
   - force action + result/final screen pairs;
   - prioritize late screens for cart, checkout, review, summary, result, and persistence claims.
4. Stabilize bounding boxes:
   - store `image_path`, `image_width`, and `image_height` per bbox;
   - render exactly that asset in the frontend;
   - only then use boxes as model-facing focused evidence.
5. Recompute metrics after each change, separating:
   - accepted gold items;
   - remaining `needs_review` items;
   - label accuracy;
   - evidence overlap.

## Short Supervisor Summary

The next improvement step is a controlled error analysis and ablation, not just more prompting. The current errors split into model bias, model intelligence limits, and pipeline retrieval limitations. The main model bias is over-fulfillment: 35 cases where the model predicts `FULFILLED` although gold is weaker or abstains. The main pipeline issue is evidence selection: among label-correct cases, 34 still have no overlap with gold evidence, especially for late cart/result/review states. I will compare the full pipeline against no-decomposition, no-top-k, and minimal all-screenshots baselines to show which components actually add value.
