# Frozen RQ3 Error-Analysis Protocol

Status: frozen before final manual coding on 23 July 2026.

Research question:

> Which requirement and evidence patterns cause verification errors, abstentions, or unsafe `FULFILLED` predictions?

## Unit of analysis

The unit is one accepted Mind2Web verification item. The primary analysis uses
the frozen 258-item benchmark and the first complete run of each prespecified
configuration. Stability repetitions are used to identify unstable predictions,
not as independent benchmark observations.

An item enters manual RQ3 coding if at least one of the following holds:

- the predicted requirement label differs from gold;
- the prediction is `ABSTAIN`;
- the prediction is `FULFILLED` while gold is any other label;
- the requirement label matches but the predicted evidence has no overlap with
  the reviewed evidence steps;
- the three-run family does not produce the same label in every run.

## Primary outcome categories

Assign exactly one primary category.

1. **Unsafe over-fulfillment**
   Prediction is `FULFILLED`, but one or more core claims are only partially
   visible, unobserved, contradicted, hidden, or outside the screenshot scope.

2. **Unsupported concrete negative**
   Prediction is `NOT_FULFILLED` without a visible contradiction. Missing
   evidence alone belongs to `ABSTAIN`.

3. **Excessive abstention**
   The decisive visible evidence is present in the screenshots supplied to the
   verifier, but the model still predicts `ABSTAIN`.

4. **Evidence-selection miss**
   Decisive evidence exists in the complete ordered flow but is absent from the
   selected top-k screenshots.

5. **Evidence-interpretation error**
   Decisive evidence is supplied, but the model misreads or fails to combine it.

6. **Label-boundary disagreement**
   The disagreement is primarily about the operational boundary between
   `FULFILLED`, `PARTIALLY_FULFILLED`, `ABSTAIN`, or `NOT_FULFILLED`, and cannot
   be reduced to missing evidence or an observable contradiction.

7. **Gold-review candidate**
   Independent inspection indicates that the primary-author label or reviewed
   evidence may need adjudication. This category never changes gold
   automatically.

## Requirement-pattern tags

Assign every applicable tag:

- `UNIVERSAL_OR_COMPLETENESS`: all, every, complete, comprehensive, any;
- `COMPARATIVE_OR_DISTINCT`: comparison, differentiation, ranking, alternatives;
- `HIDDEN_BACKEND_OR_EXTERNAL`: backend truth, authentication enforcement,
  delivery, availability, validity, external effect, or security;
- `PERSISTENCE_OR_CROSS_STEP`: state must persist across pages, sessions, or
  subsequent visits;
- `LATE_RESULT_OR_CART_STATE`: result, review, summary, cart, checkout, or final
  state occurs late in the flow;
- `MULTI_SCREEN_COMPOSITION`: the decision requires combining evidence from
  multiple non-adjacent screens;
- `NEGATION_OR_CONTRASTIVE`: requirement was deliberately altered or negated;
- `LABEL_SCHEMA_AMBIGUITY`: wording does not map cleanly to one supplied label;
- `ORDINARY_LOCAL_UI`: none of the preceding patterns applies.

## Evidence-pattern tags

- `DECISIVE_STEP_SELECTED`;
- `DECISIVE_STEP_NOT_SELECTED`;
- `ONLY_ENTRY_POINT_VISIBLE`;
- `ACTION_WITHOUT_RESULT`;
- `PARTIAL_CLAIM_COVERAGE`;
- `NO_OBSERVABLE_PROXY`;
- `LATE_STEP`;
- `CROSS_STEP_STATE`;
- `EVIDENCE_CORRECT_BUT_RATIONALE_WRONG`;
- `LABEL_CORRECT_BUT_TRACEABILITY_WRONG`.

## Coding procedure

1. Hide model identity during manual category coding where practicable.
2. Inspect requirement text and the complete ordered flow.
3. Record the gold label and reviewed evidence.
4. Inspect the exact screenshots supplied to the evaluated configuration.
5. Assign one primary outcome category and all applicable pattern tags.
6. Record a one-sentence rationale referring only to visible evidence.
7. Mark uncertain cases for adjudication rather than resolving them by
   assumption.
8. Count categories once per item; report multi-valued pattern tags separately.

## Prespecified quantitative summaries

- category counts and percentages among all label errors;
- category counts among unsafe `FULFILLED` predictions;
- abstention reasons by requirement-pattern tag;
- error rates for full-flow versus top-4 evidence;
- error rates for raw requirements versus gated decomposition;
- three-run instability counts and the categories of unstable Qwen items;
- label-correct but evidence-incorrect cases as a separate traceability result.

All percentages must state their denominator. Categories are descriptive because
the benchmark contains only 13 flows and was not sampled to estimate population
prevalence.

## Frozen qualitative cases

1. **Positive observable case — Amtrak `REQ-01`**
   The primary navigation and expanded experience categories are directly
   visible. Use this to demonstrate a defensible `FULFILLED` label with
   step-level evidence.

2. **Missed late state — Six Flags flow 10 `REQ-09`**
   The complete-flow run correctly identifies the visible quantity adjustment,
   while the gated top-4 run abstains without decisive evidence. Primary
   category: `Evidence-selection miss`; tags:
   `LATE_RESULT_OR_CART_STATE`, `DECISIVE_STEP_NOT_SELECTED`.

3. **Hidden authentication outcome — AMC Theatres `CONTR-03`**
   Gold is `ABSTAIN`, while gated top-4 predicts `FULFILLED`. Screenshots do not
   prove authentication enforcement. Primary category:
   `Unsafe over-fulfillment`; tags: `HIDDEN_BACKEND_OR_EXTERNAL`,
   `ACTION_WITHOUT_RESULT`.

4. **Universal coverage — Amtrak `CONTR-04`**
   Visible dining resources support only part of the universal claim, but
   gated top-4 predicts `FULFILLED`. Primary category:
   `Unsafe over-fulfillment`; tags: `UNIVERSAL_OR_COMPLETENESS`,
   `PARTIAL_CLAIM_COVERAGE`.

5. **Cross-visit persistence — GameStop `CONTR-01`**
   Gold is `PARTIALLY_FULFILLED`, while gated top-4 predicts `FULFILLED`.
   Current-page store context is visible, but persistence on all pages and a
   subsequent visit is not. Primary category: `Unsafe over-fulfillment`; tags:
   `PERSISTENCE_OR_CROSS_STEP`, `NO_OBSERVABLE_PROXY`.

These cases are frozen as examples, not selected after category-level effect
sizes are calculated.
