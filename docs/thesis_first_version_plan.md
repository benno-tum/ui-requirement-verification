# First Thesis Version Plan

Working title: **Automated UI Requirement Verification from Ordered Screenshot Sequences**

Examiner: Prof. Dr. Stefan Wagner

Supervisor: Mohamed Ben Salha
Registered timeframe: 2 April 2026 to 3 August 2026

This is the current writing roadmap. The detailed subsection plan and bibliography review are in [`thesis_structure_and_bibliography_audit_2026-07-21.md`](thesis_structure_and_bibliography_audit_2026-07-21.md). Quantitative sources, inconsistencies, and missing experiments are maintained in [`thesis_evidence_audit.md`](thesis_evidence_audit.md). Drafted prose remains in [`thesis_first_draft.md`](thesis_first_draft.md).

## 1. Thesis Position

The thesis studies whether textual UI requirements can be verified against ordered screenshot flows with explicit, inspectable evidence and principled uncertainty.

The main claim should be:

> UI requirement verification from screenshots is not only a label-prediction task. It is a traceability and uncertainty task. A verifier must connect each decision to visible states in an ordered flow and must preserve uncertainty when those states do not establish the requirement.

The thesis must not claim that screenshots prove hidden backend truth or that an evidence-first configuration necessarily outperforms whole-flow prompting. The current evidence shows that explicit claims and evidence make decisions inspectable and failures measurable, while the strongest current label result comes from a whole-flow stronger-model configuration.

## 2. Scope and Formal Target

Plan for approximately **42 pages of core text**, with a working range of **40 ± 5 pages**, excluding front matter, bibliography, and appendices. TUM CIT does not publish one universal Informatics page count; confirm this working target with the supervisor.

The final template must include:

- English and German titles on the first page;
- examiner and supervisor names including academic titles;
- submission date;
- no matriculation number or unrelated personal information;
- submission through the CIT Portal within the four-month Informatics timeframe;
- a supervisor-approved and transparent declaration of AI-tool use.

Use academic English and author–year citations consistently.

## 3. Research Questions

**RQ1:** How accurately can multimodal models apply a provided, application-specific verification label schema to UI-observable textual requirements using ordered screenshot flows?

**RQ2:** How do claim decomposition and screenshot selection affect label accuracy, evidence traceability, and cost relative to direct whole-flow verification?

**RQ3:** Which requirement and evidence patterns cause verification errors, abstentions, or unsafe `FULFILLED` predictions?

RQ2 is deliberately neutral and must be answered through a factor-controlled claim-policy by screenshot-selection matrix. RQ3 characterizes observed abstentions and unsafe positive predictions; it does not require or support a causal claim that abstention itself improves safety. PURE remains exploratory material rather than a numbered research question.

## 4. Recommended Structure and Page Budget

| Section | Target pages | Purpose |
|---|---:|---|
| 1 Introduction | 4 | Motivation, problem, gap, RQs, contributions, and scope. |
| 2 Foundations and Related Work | 6 | Requirements, traceability, GUI verification, UI agents, grounding, and abstention. |
| 3 Research Design and Problem Formulation | 4 | Formal task, evaluability, labels, claims, evidence, and visible/hidden boundary. |
| 4 Verification Approach and Implementation | 7 | Ordered screen handling, claim policy, evidence selection, verification, aggregation, grounding, and workbench. |
| 5 Benchmark Construction and Annotation | 5 | Mind2Web-derived data, construction funnel, contrastive items, review, statistics, and PURE. |
| 6 Evaluation | 10 | Configurations, metrics, main results, evidence, ablations, efficiency, UI evaluability, and errors. |
| 7 Discussion | 4 | Direct RQ answers, implications, threats, and limitations. |
| 8 Conclusion | 2 | Contributions, concise answers, and future work. |
| **Core text** | **42** | Excludes abstracts, lists, bibliography, and appendices. |

The supplied 1.0-graded chair thesis uses the same broad separation of foundations, methodology, implementation, evaluation, discussion, and conclusion. Its 52 pages of core text are a structural reference, not a mandatory target. This thesis keeps benchmark construction as its own chapter because annotation and evidence policy are central contributions.

## 5. Chapter Deliverables

### 1 Introduction

Open with rapid progress in coding agents but qualify the productivity argument. Agent capabilities have advanced quickly; measured end-to-end productivity remains context-dependent. As candidate implementations become cheaper to generate, specifying intent and verifying behaviour become relatively more important.

Then establish the text/visual-state mismatch, incomplete observation risk, research gap, RQs, contributions, and visible-UI scope. Use Kwa et al. (2025), SWE-bench, and Becker et al. (2025) for the opening argument. Add Kretzer et al. (2025) as the closest user-story-to-GUI work.

### 2 Foundations and Related Work

Organize around six themes:

1. requirements ambiguity and traceability;
2. GUI verification and ordered state;
3. multimodal UI agents and trajectory datasets;
4. requirement-to-UI and cross-modal verification;
5. visual grounding and evidence localization;
6. abstention and selective prediction.

End with a comparison table and a synthesis of the unresolved gap. Prefer final publisher versions over arXiv where available.

### 3 Research Design and Problem Formulation

Define ordered screenshot flow, requirement, atomic claim, UI evaluability, evidence, requirement labels, claim statuses, and aggregation. State the evidence contract explicitly:

- `FULFILLED` requires support for all central observable claims;
- missing evidence alone is not `NOT_FULFILLED`;
- hidden or external outcomes remain partial or undecidable unless their visible proxy is exactly the requirement target.

Use Amtrak as the positive running example and a late-state or hidden-result case as the contrast.

### 4 Verification Approach and Implementation

Describe the implemented behaviour rather than source-file chronology:

1. preserve ordered screen representations;
2. predict UI evaluability and optionally handle claims;
3. select all screenshots or lexical top-k evidence;
4. perform multimodal claim verification;
5. apply deterministic safety-aware aggregation;
6. localize evidence with candidate marks as a separate traceability output;
7. expose outputs in the annotation workbench and frozen run artifacts.

Distinguish provided benchmark claims from realistic raw-requirement runs. Treat semantic aggregation as an ablation over frozen claim outputs. The current test suite passes **225 tests** as of 23 July 2026; this validates implementation consistency, not scientific correctness.

### 5 Benchmark Construction and Annotation

Current Mind2Web-derived snapshot:

- 13 flows;
- 100 candidate requirements;
- 173 reviewed source requirements;
- 85 contrastive verification items;
- 258 accepted verification items;
- 541 claims;
- labels: 172 fulfilled, 45 partial, 33 abstain, and 8 not fulfilled.

Explain harvested, candidate, reviewed source, contrastive, and verification-gold stages. Generated text is not ground truth before review. “Accepted” means primary-author review and is not inter-annotator agreement.

Include temporal benchmark facts in this chapter because they justify ordered-flow verification. Keep PURE exploratory. The current material contains 31 accepted Split/Merge items with 78 claims and 11 accepted Mashboot items, but most provenance is Codex-draft and Mashboot review was post-hoc. PURE figures are intended-design artifacts rather than execution traces.

### 6 Evaluation

Every configuration table must identify the benchmark version, flows, item and prediction counts, coverage, model, prompt, claim policy, screenshot strategy, aggregation, failures, and cost basis.

Primary metrics are accuracy, macro-F1, per-class scores, false fulfillment, abstention, prediction coverage, evidence hit@k/recall@k/MRR, claim matching where meaningful, runtime, failures, and estimated cost. Add confidence intervals and account for requirements clustered within 13 flows.

Current factor-controlled full-benchmark RQ2 snapshot (Gemini 3.1 Flash-Lite, 23 July 2026):

| Configuration | Items | Accuracy | Macro-F1 | False fulfillment | Abstain | Evidence MRR |
|---|---:|---:|---:|---:|---:|---:|
| Raw requirements, all screenshots | 258 | 79.5% | 0.511 | 10.6% | 19.0% | 0.716 |
| Gated automatic decomposition, all screenshots | 258 | 79.1% | 0.532 | 12.4% | 17.1% | 0.734 |
| Raw requirements, lexical top-4 | 258 | 71.3% | 0.387 | 11.0% | 27.9% | 0.621 |
| Gated automatic decomposition, lexical top-4 | 258 | 73.6% | 0.511 | 10.4% | 26.0% | 0.607 |

These runs have full coverage, no recorded fallbacks or failures, and differ only in claim and screenshot policy. A paired 10,000-sample bootstrap over complete flows shows a clear loss from top-4 for raw requirements in accuracy, macro-F1, and MRR; decomposition effects are mixed and depend on screenshot policy. The results remain preliminary until the code/benchmark state is cleanly frozen and the statistical method is documented with a citation. The older 201-item comparison is historical and should not remain the headline table.

For RQ1, the matched raw/all comparison gives 79.5% accuracy for Gemini 3.1 Flash-Lite and 73.3% for Gemini 2.5 Flash-Lite. The paired accuracy difference is 6.2 percentage points (flow-cluster bootstrap 95% CI 1.6 to 10.8), with 83.3% raw inter-model label agreement and Cohen's kappa 0.616. A hosted open-weight Qwen3-VL-8B-Instruct raw/shared-top-4 baseline also completed with 71.3% accuracy, 0.356 macro-F1, 18.5% false fulfillment, and 0.622 evidence MRR. Against the matched Flash-Lite raw/shared-top-4 condition, it has equal accuracy and 81.0% label agreement (kappa 0.559), but a 7.4-percentage-point higher false-fulfillment rate.

Prioritize the controlled all-screenshots versus top-k and claim-policy matrix.
Evaluate region grounding as a separate traceability output rather than an
intervention on label accuracy. Report coordinate validity, localizability,
coverage, relevance, sufficiency, `NO_VISIBLE_REGION`, error categories, and
the single-author limitation after the frozen author audit. Evaluate model UI
evaluability separately. The earlier 72-item prediction-hidden pilot was
stopped after nine clear cases because the author had inspected prior outputs.
Replace it with a qualitative audit of every reference-versus-deterministic-
classifier disagreement. Do not calculate accuracy or agreement from this
disagreement-only set.

### 7 Discussion

Answer RQ1–RQ3 directly. Discuss whether the models follow the supplied label semantics, why traceability can be useful even without winning label metrics, why retrieval and reasoning are separate bottlenecks, and why finite screenshot flows cannot prove hidden outcomes. Cover construct, internal, external, and reliability validity, including generated requirements, single-author gold, flow clustering, class imbalance, model drift, PURE provenance, and licensing.

### 8 Conclusion

Summarize completed contributions and provide concise final RQ answers. Limit future work to concrete extensions: independent review, better temporal retrieval, calibrated uncertainty, larger heterogeneous data, and stronger region grounding.

## 6. Evidence and Reporting Rules

- Use only denominator-compatible results in main tables.
- Never combine runs with different models, prompts, benchmark versions, claim policies, screenshot strategies, or fallback behaviour as if they were one controlled comparison.
- Do not use 169/259, 173/258, or the stored 31.8% batched metric as current performance.
- Do not repeat the outdated 201-accepted statement.
- Do not combine 100 Mind2Web candidates with PURE candidates without naming both sources.
- Do not present Mashboot as blinded gold.
- Do not interpret absent evidence metrics as zero.
- Do not present generated bounding boxes as correct without human evaluation.
- Do not imply that screenshots prove backend correctness, security, persistence, completeness, external delivery, or all reachable states.

## 7. Remaining Work

### Before a Complete First Version

- [x] Draft Chapters 2–4 using the agreed structure.
- [x] Expand the dataset, evaluation, discussion, and conclusion prose around
  the frozen results.
- [ ] Correct and export final bibliography metadata in the selected thesis
  typesetting system.
- Confirm chapter plan, page target, and AI-use disclosure with the supervisor.

### Before Final Results

- [x] Execute the six prespecified stability repetitions from a clean commit and
  generate the three-run stability summary.
- [x] Retain the flow-cluster bootstrap, aggregate metrics, sanitized execution
  manifests, and hashes in the curated replication package.
- [x] Freeze five qualitative cases and the RQ3 error-category protocol.
- [x] Prepare a blinded, stratified 44-item second-review form covering every
  flow and label. The form remains unused because the final plan does not
  require a second annotator.
- [x] Record the resulting single-annotator limitation and prohibit claims
  about independent validation, inter-rater agreement, or adjudication.
- [x] Add Field and Welsh (2007) as the cluster-bootstrap method citation.
  Treat the intervals as descriptive sensitivity intervals because only 13
  flows are available.
- [x] Complete the matched chronology-destroying order-unavailable robustness
  run with Gemini 3.1 Flash-Lite. It covers 258/258 items with zero fallbacks or
  failures and is analyzed against the ordered `fl_raw_all` baseline using
  paired flow-cluster bootstrap intervals.
- [ ] Complete the author-conducted region-grounding audit and insert
  relevance, sufficiency, coverage, localization-abstention results, and the
  single-annotator limitation.
- [ ] Complete the 81-item author audit containing every UI-evaluability
  disagreement across the 300 accepted Mind2Web/PURE items. Report resolution
  categories and recurring label-boundary causes, not accuracy, kappa, or
  prevalence.
- [x] Document a conservative aggregate-only Mind2Web/PURE release boundary.
- [ ] Obtain written permission before releasing Mind2Web test-derived per-item
  annotations or PURE text/figure derivatives.
- [ ] Select a repository code license with the supervisor or chair.

## 8. Current Main Argument

If the final results remain consistent with the present evidence, the conclusion should be approximately:

> Ordered screenshot flows make visible UI requirement verification measurable, but they do not remove uncertainty created by incomplete observation. Whole-flow multimodal models provide a strong label baseline, while explicit claim and evidence structures make decisions traceable and reveal retrieval and reasoning failures. The main difficulties concern partial evidence being over-generalized, decisive late states being missed, universal or comparative wording, and obligations whose truth is hidden from screenshots. Reliable verification therefore requires both effective evidence use and conservative reasoning about what the visible flow can establish.
