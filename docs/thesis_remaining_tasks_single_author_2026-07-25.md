# Remaining Thesis Tasks: Single-Author Evaluation

Status: prepared on 25 July 2026.

This plan replaces the earlier assumption that an independent second reviewer
would complete the 44-item verification-label form. The form remains in the
repository as provenance but is not part of the final evaluation. The thesis
must not claim independent gold validation, inter-rater agreement, or human
adjudication.

## 1. What is already complete

- The controlled 2x2 Gemini 3.1 Flash-Lite matrix covers all 258 Mind2Web
  verification items.
- The Gemini 2.5 Flash-Lite and hosted Qwen3-VL-8B comparisons are complete.
- Three-run stability data, a 10,000-sample flow-cluster bootstrap, cost and
  runtime metadata, and the offline abstention-policy counterfactual exist.
- Five qualitative cases and the RQ3 error taxonomy are frozen.
- The curated replication package currently passes its secret and personal-path
  release check.

No additional paid model run is required for the three research questions.

The prepared blank forms are:

- `data/annotations/evaluation_audits/single_author_final_20260725/ui_evaluability_disagreement_audit_form.json`
  with all 81 disagreements between the existing author reference and the
  deterministic classifier across 300 accepted Mind2Web/PURE items;
- `data/annotations/evaluation_audits/single_author_final_20260725/v7_region_author_audit_form.json`
  with 52 deterministically sampled region-bearing claim-step groups, four per
  Mind2Web flow, plus all eight non-missing claims for which V7 returned no
  visible region.

The forms have already been generated and frozen. Do not run the preparation
command before reviewing them. The following command is retained only for
rebuilding a fresh, unanswered audit package if the current files are
deliberately discarded:

```bash
python scripts/prepare_single_author_thesis_audits.py
```

Once any response has been entered, never regenerate or overwrite the forms.
Complete both manual audits at `http://127.0.0.1:5173/author-audit`; the UI
saves directly into the frozen forms and displays completion progress.

## 2. Statistical results freeze

Run these commands from the repository root:

```bash
python scripts/analyze_thesis_final_matrix.py
python scripts/analyze_thesis_run_stability.py
python scripts/audit_thesis_replication_package.py --check-only
```

Acceptance criteria:

- 13 flows and 258 items;
- no missing predictions;
- the regenerated controlled-matrix results match the curated artifacts;
- the replication-package audit reports zero findings.

The bootstrap resamples complete flows because items within a flow share
screenshots and task context. Cite Field and Welsh (2007), *Bootstrapping
Clustered Data*, DOI `10.1111/j.1467-9868.2007.00593.x`. Since only 13 flows
are available, call the percentile intervals descriptive sensitivity intervals.
Do not use them as proof of population-level significance.

## 3. RQ3 author coding

Apply `docs/rq3_error_analysis_protocol_2026-07-23.md` to every eligible item
from the frozen first run of each prespecified condition.

For every included item, record:

- anonymized condition;
- flow and requirement ID;
- gold and predicted label;
- whether the decisive step was supplied;
- one primary outcome category;
- all applicable requirement and evidence tags;
- one sentence tied to visible screenshot evidence;
- whether the case may require a post-freeze author correction.

Keep the benchmark unchanged during coding. If a likely gold error is found,
place it in a separate amendment log. Decide amendments only after the first
coding pass and regenerate every affected metric. Report this as author
re-inspection, not adjudication.

Required outputs:

- counts and percentages with explicit denominators;
- unsafe-`FULFILLED` categories;
- abstention categories;
- raw/all versus raw/top-4 and gated/all versus gated/top-4 comparisons;
- the five frozen qualitative examples.

## 4. UI-evaluability disagreement audit

The UI-evaluability labels were created by the thesis author. A final
prediction-hidden pilot was stopped after nine items because the author had
inspected earlier labels and classifier outputs. Its responses were removed
from the active audit. The replacement is an explicitly unblinded qualitative
analysis of every disagreement.

Procedure:

1. Review all 81 items selected solely because the two labels differ.
2. Inspect the existing author label, deterministic classifier label,
   classifier rationale, detected hidden-property terms, claim composition,
   original note, and generated divergence hypothesis.
3. Select the final label. Choosing the current reference acts as a reviewed
   skip; choosing another label automatically records an amendment
   recommendation.
4. A free-text note is optional and is not required for routine cases.
5. Keep amendment recommendations separate until the complete pass is frozen.
6. Apply approved amendments together and regenerate every affected aggregate.

Use `/author-audit`. The interface intentionally exposes both labels and the
available reasons. The generated divergence explanation is diagnostic only and
must not be treated as the correct answer.

This disagreement-conditioned set cannot estimate classifier accuracy,
annotator agreement, kappa, or corpus prevalence. Report resolution counts and
recurring construct-boundary patterns with an explicit denominator of 81.

## 5. V7 region-grounding audit

Region grounding is evaluated separately from requirement-label accuracy. The
V7 localization package preserves the source labels by construction.

Before viewing aggregate localization scores, freeze a stratified sample from
`gemini25flash_omnimark_v7_factcoverage_bbox_allflows_01_13_20260721`.
The sample must cover:

- all 13 flows;
- text and non-text evidence;
- single-region and multi-region claims;
- supported, partial, contradicted, and missing/hidden claim states;
- all eight non-missing `NO_VISIBLE_REGION` cases;
- candidate regions and supplemental regions.

The prepared 60-item form implements this scope with deterministic within-flow
diversity sampling over claim status, region count, and region source.

For each sampled claim-step, record:

- applicability: single region, multiple regions, whole screen/transition, or
  no visible region;
- whether an acceptable candidate existed;
- geometric validity;
- semantic relevance;
- evidential sufficiency;
- missing facts for insufficient regions;
- error category;
- whether localization abstention was appropriate.

Report candidate coverage and selection quality separately. A geometrically
correct box can still be insufficient. Results are a single-author quality
audit and must not be described as independently validated localization
accuracy.

## 6. Thesis insertion points

After the manual audits, replace the four pending-result comments in
`docs/thesis_first_draft.md`:

1. UI-evaluability disagreement-audit method and qualitative boundary results;
2. performance stratified by the frozen labels only if any recommended
   amendments have been applied and all affected metrics regenerated;
3. V7 region relevance, sufficiency, coverage, and abstention results;
4. limitations of the single-author reference and region audit.

Keep bounding-box findings in a separate evaluation subsection. Do not present
them as an accuracy-improvement factor for RQ2.

## 7. Supervisor and release decisions

These tasks require a decision rather than another experiment:

- confirm that a single-author reference set is acceptable for the bachelor
  thesis when disclosed as a validity limitation;
- confirm that the 13-flow bootstrap is reported as descriptive sensitivity
  analysis;
- decide whether region grounding belongs in the main evaluation or an
  exploratory subsection;
- obtain written permission before publishing Mind2Web-derived per-item
  annotations or PURE text/figure derivatives;
- select a repository code license before describing the code as open source;
- confirm the wording of the AI-use disclosure.

## 8. Final validity wording

Use language equivalent to:

> All reference annotations and qualitative audits were conducted by the thesis
> author using frozen label and evidence policies. The evaluation therefore
> measures agreement with a documented author-reviewed reference standard,
> rather than an independently established ground truth. Prediction-hidden
> re-audits and explicit amendment logs reduce accidental inconsistency but do
> not replace independent validation.
