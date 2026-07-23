# Thesis Evidence Audit

Working title: **Automated UI Requirement Verification from Ordered Screenshot Sequences**

Audit date: **21 July 2026**

Purpose: source-of-truth register for the first thesis draft and the final evaluation.

This document separates facts that can already be used in the thesis from historical snapshots, exploratory results, and work that is still required. A number appearing here is not automatically a final thesis result. Final results must be reproduced from a frozen benchmark and a named run configuration.

## 1. Formal Scope and Submission Constraints

The central TUM School of Computation, Information and Technology (CIT) page for Informatics theses specifies a four-month deadline for a Bachelor's Thesis in Informatics and submission through the CIT Portal. It also specifies the required cover and first-page information. The first page must contain the thesis title in English and German, the examiner and supervisor names including academic titles, and the submission date. The student registration number and unrelated personal information must not be included. The TUM and school logos are optional. Source: [TUM CIT, Thesis and Completing your Studies in Informatics](https://www.cit.tum.de/en/cit/studies/students/thesis-completing-your-studies/informatics/).

The central CIT page does not prescribe a universal page count for Informatics. Guidance published by individual TUM chairs varies. For example, the [Chair of Communication Networks](https://www.ce.cit.tum.de/en/lkn/student-thesis/thesis-presentation-templates/writing-your-thesis/) gives approximately 30–40 pages for a bachelor's thesis, while the [sebis chair](https://www.cs.cit.tum.de/sebis/student-theses-guided-research/guidelines-for-student-research-projects/thesis-writing-tips/) gives approximately 40–60 pages. These are local guidelines rather than a binding rule for the Chair of Software Engineering. The working target for this thesis is therefore **40 ± 5 pages of core text**, excluding front matter, bibliography, and appendices. This target must be confirmed with Mohamed Ben Salha.

The planned front matter is:

1. Cover.
2. First/title page with the English and German titles.
3. Declaration of originality and, if required by the chair, a declaration of AI-tool use.
4. Abstract of approximately half a page.
5. Table of contents.
6. Lists of figures, tables, and abbreviations when their length justifies separate lists.

TUM guidance treats generative AI tools as aids whose use must be explicitly permitted by the responsible instructor or examination rules and transparently documented when allowed. Because Codex is being used for planning, evidence auditing, and language drafting, the permitted form of use and the required disclosure must be confirmed with the supervisor before submitted prose is finalized. Source: [TUM ProLehre, Use AI wisely](https://www.prolehre.tum.de/en/prolehre/programs-services/teaching-development/use-ai-wisely/).

## 2. Current Implementation Status

The repository contains a runnable prototype rather than only a conceptual proposal. Its implemented parts include:

- a modular evidence-first verification pipeline;
- requirement understanding and claim decomposition;
- lexical and optional model-based evidence retrieval;
- screenshot-grounded Gemini claim verification;
- conservative requirement-level aggregation;
- structured label, evidence, uncertainty, and run metadata schemas;
- a backend API and React annotation workbench;
- scripts for data preparation, review bundles, pipeline execution, reaggregation, and metric calculation;
- PURE loaders and extraction/evaluation preparation.

The current automated test suite passes:

```text
203 passed
```

This was checked on 21 July 2026 with `python -m pytest -q` (`203 passed in 5.71s`). The test result supports the claim that the checked-in implementation is internally consistent and runnable. It does not establish scientific validity, model reliability, or external generalization.

The mature evaluated evidence granularity remains **screenshot-step-level**. The repository now contains end-to-end candidate-mark grounding runs over all 13 flows, including a July 21 joint Flash-Lite run with 588 stored boxes/evidence records and a V7 localization run with 697 valid regions. These outputs demonstrate that localization is implemented; they do not establish localization accuracy. The existing region audits are not blind human reviews, and relevance and sufficiency remain unvalidated. The thesis must either add a prediction-independent bounding-box evaluation or present region grounding only as an exploratory extension.

## 3. Dataset Source of Truth

### 3.1 Mind2Web-Derived Benchmark

The current main benchmark uses 13 ordered web interaction flows derived from Mind2Web artifacts stored in the repository. The current annotation snapshot is:

| Quantity | Current value | Source |
|---|---:|---|
| Mind2Web flows | 13 | `data/annotations/verification_gold/01_*` through `13_*` |
| Candidate requirements | 100 | `data/annotations/requirements_candidate/01_*` through `13_*` |
| Reviewed source/gold requirements | 173 | `data/annotations/requirements_gold/01_*` through `13_*` |
| Contrastive verification items | 85 | Verification items whose `source_type` is `requirements_candidate` |
| Verification items | 258 | `data/annotations/verification_gold/01_*` through `13_*` |
| Accepted verification items | 258 | `review_status == accepted` |
| Gold claims | 541 | Sum of claim arrays in the 258 verification items |

The 258 verification items consist of the 173 reviewed source requirements plus 85 reviewed contrastive items. The distinction matters: a contrastive item is not one of the 100 initial candidates merely because its `source_type` is `requirements_candidate`. It is a deliberately modified evaluation requirement added to create partial, negative, or undecidable cases.

Current label distribution:

| Label | Count | Share |
|---|---:|---:|
| `FULFILLED` | 172 | 66.7% |
| `PARTIALLY_FULFILLED` | 45 | 17.4% |
| `ABSTAIN` | 33 | 12.8% |
| `NOT_FULFILLED` | 8 | 3.1% |
| **Total** | **258** | **100%** |

Current UI-evaluability distribution:

| UI evaluability | Count |
|---|---:|
| `UI_VERIFIABLE` | 192 |
| `PARTIALLY_UI_VERIFIABLE` | 62 |
| `NOT_UI_VERIFIABLE` | 4 |

All 258 Mind2Web items are marked accepted and annotated by Benno. In the thesis, “accepted” must therefore be described as completion of the primary author's review, not agreement between independent annotators. The absence of an independent second review remains a threat to internal validity.

### 3.2 Requirement Construction Process

The benchmark construction stages should be described as follows:

1. **Harvested requirements** are broad hypotheses derived from the flow and associated artifacts. They maximize coverage and may be redundant, vague, or unsupported.
2. **Candidate requirements** are filtered or rewritten proposals. They are not ground truth.
3. **Gold/source requirements** are human-reviewed requirement texts promoted into the benchmark.
4. **Contrastive requirements** deliberately strengthen, negate, or add conditions to source requirements to create difficult non-positive cases. Their automatically suggested labels are not gold until reviewed.
5. **Verification-gold items** contain the final requirement text, UI evaluability, requirement label, claims, claim statuses, evidence steps, rationale, and uncertainty reasons used for evaluation.

This separation is necessary to address circularity. A model-generated requirement cannot become a valid reference merely because another model later agrees with it. Human review, explicit evidence, and disclosure of the generation process are required.

### 3.3 PURE Material

PURE is secondary external material intended to test the approach on longer and more document-dependent requirements.

Current Split/Merge snapshot:

- 31 accepted verification items;
- 78 claims;
- labels: 23 `FULFILLED`, 4 `PARTIALLY_FULFILLED`, and 4 `ABSTAIN`;
- annotation provenance: 23 items attributed to Benno and 8 retained as Codex drafts.

Split/Merge has progressed beyond the older 5/29 accepted snapshot, but it still requires provenance-aware reporting and an independent review. Some items are researcher-contextualized from descriptive document passages rather than formally numbered requirements. The most recent run also became slightly stale when the annotation set changed from 74 to 78 claims.

Current Mashboot snapshot:

- 11 accepted verification items;
- labels: 3 `FULFILLED`, 5 `PARTIALLY_FULFILLED`, and 3 `ABSTAIN`;
- annotation provenance: 1 item attributed to Benno and 10 retained as Codex drafts;
- the annotation process began after the relevant predictions had been inspected.

Mashboot labels are therefore post-hoc and cannot serve as blinded gold even though their review status is now accepted. PURE remains suitable for exploratory analysis of extraction, contextualization, compound requirements, UI evaluability, and document-to-UI consistency. It is not equivalent evidence for ordered execution-flow verification because its images usually depict intended design rather than observations of a running implementation.

## 4. Current Full-Benchmark Preliminary Results

The final primary Gemini 3.1 Flash-Lite matrix now covers all 13 flows and produces **258/258 predictions in every cell**. The four cells use the same model, prompt, label schema, aggregation, benchmark, execution date, and maximum of eight claims per call. They vary only claim policy and screenshot policy, so they form the current factor-controlled RQ2 comparison. All results remain preliminary until the code and benchmark are frozen in a clean commit and uncertainty analysis is added.

| Configuration | Items / flows | Claim and screenshot strategy | Accuracy | Macro-F1 | False fulfillment | Abstain | Evidence MRR | Calls / failures | Tokens | Estimated cost |
|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| Gemini 3.1 Flash-Lite | 258 / 01–13 | Raw requirements; all screenshots | 79.5% | 0.514 | 10.6% | 19.0% | 0.716 | 39 / 0 | 612,429 | $0.2817 |
| Gemini 3.1 Flash-Lite | 258 / 01–13 | Gated automatic decomposition; all screenshots | 79.1% | 0.536 | 12.4% | 17.1% | 0.734 | 41 / 0 | 653,388 | $0.3002 |
| Gemini 3.1 Flash-Lite | 258 / 01–13 | Raw requirements; lexical top-4 | 71.3% | 0.387 | 11.0% | 27.9% | 0.621 | 39 / 0 | 433,519 | $0.2778 |
| Gemini 3.1 Flash-Lite | 258 / 01–13 | Gated automatic decomposition; lexical top-4 | 73.6% | 0.518 | 10.4% | 26.0% | 0.607 | 41 / 0 | 421,723 | $0.2394 |

The complete 2x2 matrix used 160 successful API calls, recorded no fallbacks or failures, and cost approximately $1.0991. The result does not support a uniform advantage for the proposed evidence-first configuration. A paired 10,000-sample bootstrap over complete flows finds that raw top-4 is worse than raw/all in accuracy (-8.1 percentage points, 95% CI -12.0 to -3.8), macro-F1 (-0.127, -0.244 to -0.043), and MRR (-0.095, -0.148 to -0.031). Gated top-4 is also worse than gated/all in accuracy (-5.4 percentage points, -10.2 to -1.1) and MRR (-0.128, -0.187 to -0.063), while its macro-F1 interval spans zero. Gated decomposition under all screenshots has mixed differences whose accuracy, macro-F1, and MRR intervals span zero; its false-fulfillment difference is +1.9 percentage points (95% CI +0.4 to +3.3). Under top-4, decomposition improves macro-F1 by 0.131 (95% CI +0.021 to +0.193). Only 13 clusters are available, so the intervals remain descriptive rather than grounds for broad generalization.

For the raw/all cell, forcing all 49 native abstentions to `NOT_FULFILLED` reduces accuracy from 79.5% to 70.2% and macro-F1 from 0.514 to 0.331 while false fulfillment remains 10.6%. For gated/top-4, forcing all 67 abstentions reduces accuracy from 73.6% to 64.3% and macro-F1 from 0.518 to 0.305 while false fulfillment remains 10.4%. These are zero-cost aggregation-policy counterfactuals, not new LLM runs. They show that blanket negative replacement is harmful but cannot establish causal safety improvement from abstention.

The matched raw/all model comparison supplies current RQ1 sensitivity evidence. Gemini 3.1 Flash-Lite exceeds Gemini 2.5 Flash-Lite by 6.2 percentage points accuracy (paired flow-cluster bootstrap 95% CI 1.6 to 10.8), 0.102 macro-F1 (0.006 to 0.218), and 0.121 evidence MRR (0.010 to 0.241). Their raw label agreement is 83.3% (78.5% to 88.1%) and Cohen's kappa is 0.616 (0.469 to 0.735). Both are commercial Google models, so this is not evidence of cross-provider or open-model generalization.

### 4.1 Run Cleanliness and Necessary Disclosures

The five completed Gemini runs are technically clean in the narrow execution sense: every run contains 13 flow files and 258 predictions, every API attempt succeeded on its first recorded attempt, and there are zero cache hits, fallbacks, or recorded failures. The four Gemini 3.1 matrix cells share the same exact model alias, prompt version, temperature, thinking level, maximum of eight claims per request, label aggregation, and execution date. The Gemini 2.5 comparison uses the same prompt and screenshot/claim strategy but its model-specific thinking budget is explicitly zero.

They are not yet a final immutable replication package. The executions were made from Git commit `b26285a5588382ede25d1ecc8b2e544918bb7b2a` with a dirty worktree. The current preflight manifest records source and gold hashes, but it was regenerated after execution rather than being an immutable clean-commit run bundle. The benchmark and outputs should therefore be frozen in a clean commit before the results are called final.

Additional disclosures are required:

- “All screenshots” means every screenshot was attached to every chunk of at most eight claims, not literally one API call per flow. The raw and gated conditions used 39 and 41 calls and repeatedly attached the same flow images across chunks.
- “Top-4” is a group-level four-image cap for batches of up to eight claims. Individual lexical retrieval selected 1,014 steps in raw/top-4 and 1,106 in gated/top-4, but only 70.6% and 70.9% of those claim-selected steps survived into the shared group attachments. Some selected evidence was therefore removed by group compression. This condition should be described as **batched shared top-4**, not per-requirement top-4.
- Gated decomposition is deterministic heuristic decomposition with no LLM fallback. It decomposes 31 of 258 requirements and yields 281 claims. The result does not evaluate an LLM claim-decomposer.
- Candidate-mark/OmniParser grounding was disabled (`grounding_candidates = null`). Bounding boxes were not disabled: the common prompt requested free-form visual regions and OCR refinement produced boxes for most cited evidence units. These boxes were neither independently reviewed nor scored. They may not be claimed as a validated contribution and their generation is part of the prompt/output workload.
- The requirements loader reads the benchmark gold JSON but only sends requirement text, identifiers, predicted claims, and screen evidence to the verifier. Gold labels and gold evidence are not referenced by the verifier code. Nevertheless, a sanitized prediction-input file would provide stronger structural protection against accidental label leakage.
- Exact commercial serving revisions and system fingerprints are unavailable. The exact model aliases, date, SDK, prompt, parameters, images, outputs, and usage are archived, but provider drift remains possible.
- The benchmark is strongly imbalanced: 172 of 258 labels are `FULFILLED`, while only eight are `NOT_FULFILLED`. Accuracy must be interpreted with macro-F1 and per-class scores.

The strongest cell, Gemini 3.1 raw/all, reaches 79.5% accuracy but only 0.514 macro-F1. Its per-class F1 values are 0.936 for `FULFILLED`, 0.286 for `PARTIALLY_FULFILLED`, 0.200 for `NOT_FULFILLED`, and 0.634 for `ABSTAIN`. It is therefore a useful but not production-ready verifier. The main optimization target is minority-label reasoning and evidence sufficiency, not headline accuracy.

### 4.2 Completed Open-Weight Baseline

A local SmolVLM2-2.2B timing run on the 16 GB M1 Pro completed one 128-token capped group in 323 seconds. The output was truncated and produced zero valid parsed claims, so all generated fallback records are invalid as benchmark evidence. A full local run would likely require many hours and retries.

A hosted Qwen3-VL-8B-Instruct OpenRouter run completed on 23 July 2026 using the frozen raw/shared-top-4 evidence groups. It produced 258/258 predictions in 39 first-attempt calls with no fallback, missing prediction, or parsing failure. OpenRouter returned Alibaba as the provider. The run recorded 255,185 prompt tokens, 24,981 completion tokens, 256.1 seconds of summed request time, and USD 0.041223 inference cost. Images were resized to a 1,600-pixel longest edge; bounding boxes were not requested.

| Items | Accuracy | Macro-F1 | False fulfillment | Abstain | Evidence MRR | Recall@1 | Recall@3 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 258 | 71.3% | 0.356 | 18.5% | 23.3% | 0.622 | 0.329 | 0.417 |

The matched Gemini 3.1 Flash-Lite raw/shared-top-4 run has the same 71.3% accuracy. Qwen is 0.030 lower in macro-F1 (flow-cluster bootstrap 95% CI -0.068 to +0.007), 7.4 percentage points higher in false fulfillment (+2.5 to +12.6), and effectively equal in evidence MRR (+0.001, -0.038 to +0.038). The models agree on 81.0% of labels (75.7% to 86.7%); Cohen's kappa is 0.559 (0.444 to 0.683). Qwen predicts only two `PARTIALLY_FULFILLED` items and one `NOT_FULFILLED` item, yielding per-class F1 values of 0.043 and 0.000 for those labels. The equal headline accuracy therefore does not imply equal safety or balanced label performance.

The Qwen weights are Apache-2.0, but this must be described as a hosted open-weight baseline rather than a fully independently reproduced local run. The provider serving stack and quantization are not exposed. The raw response archive records the provider, model slug, usage, cost, prompts, outputs, source-manifest hashes, and preprocessing settings.

The following older full-coverage configurations remain useful contextual evidence. They are denominator-compatible but not a factor-controlled comparison because model strength, claim policy, screenshot selection, execution grouping, and grounding differ.

| Configuration | Items / flows | Prompt, claim, and evidence strategy | Accuracy | Macro-F1 | False fulfillment | Abstain | Coverage | Estimated cost |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Gemini 3.1 Pro preview | 258 / 01–13 | Single call per flow; all screenshots; 541 provided claims; grounded evidence output; deterministic aggregation | 78.3% | 0.560 | 7.6% | 6.2% | 100% | Not normalized in the current summary |
| Gemini 3.1 Flash-Lite | 258 / 01–13 | Single joint call per flow; all screenshots; 541 provided claims; OmniParser/OCR candidate grounding; deterministic aggregation | 76.7% | 0.528 | 12.4% | 7.4% | 100% | $0.484779 |
| Gemini 3.1 Flash-Lite | 258 / 01–13 | Raw requirements; no decomposition; lexical top-4; joint verification and candidate grounding; 29 calls | 72.1% | 0.449 | 10.5% | 27.1% | 100% | $0.561202 |

Exact metric files:

- `data/generated/evaluation/gemini31pro_singlecall_allimages_mind2web13_20260719_metrics_recomputed.json`
- `data/generated/evaluation/gemini31flashlite_joint_omnimark_singlecall_mind2web13_20260721_metrics.json`
- `data/generated/evaluation/gemini31flashlite_realistic_topk4_no_claims_mind2web13_20260721_metrics.json`

Comparable screenshot-step evidence metrics are:

| Evidence metric | Pro, all screenshots, provided claims | Flash-Lite joint, provided claims | Flash-Lite top-4, raw requirements |
|---|---:|---:|---:|
| MRR | 0.899 | 0.808 | 0.606 |
| Hit@1 | 0.884 | 0.795 | 0.593 |
| Hit@3 | 0.915 | 0.822 | 0.620 |
| Recall@1 | 0.481 | 0.434 | 0.334 |
| Recall@3 | 0.639 | 0.529 | 0.358 |

The provided-claim runs each match all 541 benchmark claim texts by construction. Their claim-status macro-F1 values are 0.331 for Pro and 0.266 for Flash-Lite. These values assess claim-status prediction given benchmark claims; they do not evaluate automatic claim decomposition.

The realistic raw-requirement run independently predicts UI evaluability. Against the gold UI-evaluability labels it reaches 79.5% raw agreement, macro-F1 0.420, unweighted Cohen's kappa 0.325, and ordinal-weighted kappa 0.354. Recall is 99.0% for `UI_VERIFIABLE`, 24.2% for `PARTIALLY_UI_VERIFIABLE`, and 0% for the four `NOT_UI_VERIFIABLE` items. This is useful auxiliary evidence but is strongly influenced by class imbalance.

### 4.3 Interpretation Allowed by the Data

The current full-benchmark snapshot supports these preliminary statements:

- Gemini 3.1 Pro has the highest current accuracy, macro-F1, lowest false-fulfillment rate, and strongest screenshot-step evidence metrics among the three full-coverage configurations.
- The realistic top-4 raw-requirement run abstains far more often and has lower macro-F1 and evidence recall. It has a lower false-fulfillment rate than the current Flash-Lite all-screen joint run, but a higher rate than Pro.
- The older contextual results do not isolate those effects. The new 2x2 matrix isolates claim and screenshot policy for Gemini 3.1 Flash-Lite, but model scale and candidate grounding remain separate questions.
- Explicit evidence output makes traceability measurable; it does not by itself prove improved label safety.
- Accuracy alone remains misleading because 172 of 258 items are `FULFILLED` and only eight are `NOT_FULFILLED`. Macro-F1, per-class results, false fulfillment, and abstention must be reported together.
- The current box outputs show region-generation coverage, not human-validated localization quality.

## 5. Historical and Inconsistent Artifacts

The following values are useful as history but must not be copied into the final result table:

| Historical value | Why it is not a current headline result |
|---|---|
| 201-item flows 01–10 comparison: 76.1% Flash-Lite whole-flow, 81.1% Pro whole-flow, 75.1% batched top-k, 20.4% deterministic | Denominator-compatible for its subset and useful as experiment history, but superseded as the headline snapshot by full-coverage 258-item runs. |
| 258-item deterministic raw/top-4 run prepared on 23 July 2026: 44.6% accuracy, 0.293 macro-F1, 33.3% false fulfillment, 10.1% abstention, evidence MRR 0.467 | Full 258-item coverage with Mind2Web-only strict evaluation. Preliminary until the code worktree is committed and the manifest is frozen. Do not compare the number directly with the historical 201-item deterministic row without explaining the changed denominator and implementation. |
| 258-item deterministic gated/top-4 run prepared on 23 July 2026: 45.3% accuracy, 0.301 macro-F1, 32.8% false fulfillment, 9.7% abstention, evidence MRR 0.464 | Zero-cost controlled decomposition baseline. The small difference from raw requirements is descriptive; confidence intervals and a paired test remain before interpreting it. |
| Offline forced-decision smoke test on the deterministic outputs | Converted 26 raw and 25 gated abstentions to `NOT_FULFILLED` with zero API calls. Accuracy dropped to 41.1% and 41.9%; false fulfillment was unchanged. This validates the policy-ablation implementation but is not evidence about LLM abstention until repeated on frozen LLM outputs. |
| Gemini 2.5 Flash-Lite raw whole-flow baseline, chunked to at most eight requirements per complete-flow call | 258/258 predictions, 73.3% accuracy, 0.412 macro-F1, 13.7% false fulfillment, 22.1% abstention, evidence MRR 0.595. Final valid run used 39 API calls with zero fallbacks/failures and recorded 368,138 tokens for approximately USD 0.0711. Treat as a low-cost commercial model baseline; it does not satisfy the separate open-model recommendation. |
| Offline forced-decision counterfactual on the valid Gemini 2.5 baseline | All 57 native abstentions became `NOT_FULFILLED`; accuracy fell to 66.7%, macro-F1 to 0.332, and false fulfillment remained 13.7%. Suitable as evidence that blanket closed-world replacement is harmful, but not as proof that all native abstentions are calibrated. |
| 169/259 = 65.3% | Assembled from the then-current run per flow, including API fallbacks and an older 259-item gold snapshot. |
| 173/258 = 67.1% | Mixed per-flow configurations selected for qualitative error analysis rather than a controlled experiment. |
| 48.6% Gemini diagnosis and 26.6% deterministic diagnosis | Only 173 predictions were present while the evaluator scored 259 gold items; missing predictions became abstentions. |
| 31.8% batched top-k in the stored `metrics.json` | The evaluator used all 258 gold items although only flows 01–10 and 201 predictions were present, producing 57 artificial missing predictions. |
| 201 accepted / 57 needs review | Outdated. The current Mind2Web files contain 258 accepted items. |
| 171/45/33/9 or 159/56/31/12 label distributions | Earlier benchmark snapshots. The current distribution is 172/45/33/8. |
| 142 candidate requirements | Combines 100 Mind2Web candidates with 42 committed PURE candidates. |
| Split/Merge 5/29 accepted and Mashboot 0/11 accepted | Outdated review-status snapshot. Current files mark 31 and 11 accepted respectively, but the provenance and post-hoc caveats remain. |

Historical cross-flow error reports remain valuable for identifying patterns, provided their counts are labeled as historical. The recurring patterns are:

- over-fulfillment from partial visible evidence;
- reluctance to abstain on hidden or unobserved outcomes;
- missed late cart, checkout, result, review, and summary screens;
- universal and comparative statements inferred from a single example;
- result correctness inferred from the presence of an input form or action button;
- persistence or external effects inferred from a transient UI state.

## 6. Evidence Suitable for Qualitative Analysis

### Amtrak Positive Example

Use the following presentation-style requirement:

> The system shall make onboard dining information and café menu resources discoverable through public site navigation without requiring the user to sign in.

Steps 1, 4, and 5 show public navigation from the Amtrak site to Onboard Dining and the Café page with menu links. The flow reaches those resources without a sign-in wall. The example is suitable for `FULFILLED` because both obligations are scoped to the visible path. It must not be generalized into proof that all routes have the correct menus or that no hidden account checks exist elsewhere.

### Late-State Retrieval Failure

Flow 10 is the clearest retrieval example. Relevant cart and checkout evidence occurs late in the flow, especially around steps 8–10. Earlier retrieval variants sometimes selected only the configuration or action screens and missed the resulting cart state. This creates under-calling and abstention even though the needed visible evidence exists. The example supports the need to retrieve action/result pairs and to evaluate evidence independently of the final label.

### Hidden-Outcome Example

A visible search form can establish that the user can enter criteria and submit a search. It cannot by itself establish that all returned results are correct or complete. Similarly, a visible menu link cannot establish route applicability, and a checkbox cannot establish long-term persistence. These examples motivate `PARTIALLY_FULFILLED` and `ABSTAIN` rather than a forced positive or negative verdict.

## 7. Missing Work Before Final Results

### Required

- Freeze the 258-item Mind2Web benchmark and record a checksum or commit identifier.
- Choose final configurations and reproduce every headline configuration over flows 01–13 from that frozen benchmark.
- Store a run manifest containing model identifier, date, prompt version, claim policy, retrieval strategy, top-k, image limits, aggregation method, retries, fallbacks, runtime, tokens, image count, and cost.
- Recompute every table from the frozen manifest rather than copying summary files by hand.
- Add an independent second review for at least a stratified sample covering every label and the main ambiguity categories; report agreement and adjudication.
- Retain the paired flow-cluster bootstrap artifact with the frozen run manifest and add a statistical-method citation. An ordered-versus-shuffled run is optional because ordering is part of the task definition rather than a current causal RQ.
- Select and freeze 3–5 qualitative cases with requirement text, gold label, prediction, evidence steps, and a short error category.
- Decide whether the completed 10,000-sample flow-cluster bootstrap is sufficient given only 13 clusters, and document the chosen statistical method and citation.
- Document Mind2Web/PURE licenses and specify which derived artifacts can be released.
- Either perform a prediction-independent relevance and sufficiency review of the bounding boxes or classify region grounding as exploratory rather than a validated contribution.

### Recommended

- Report metrics separately for original and contrastive requirements.
- Report metrics by UI evaluability and by requirement-pattern category.
- Report per-flow values only as diagnostics, not as independent test samples.
- Audit step indexing so that all stored and evaluated evidence uses the same convention.
- Include exact model identifiers rather than marketing-family names alone.
- Distinguish cost estimates based on pricing assumptions from billed cost.

## 8. Bibliography and Source Register

The table below is a working register. Primary papers and official institutional pages should be preferred over secondary descriptions.

| Source | Venue / identifier | Type | Thesis use |
|---|---|---|---|
| Kwa et al. (2025), *Measuring AI Ability to Complete Long Tasks* | arXiv:2503.14499 | Empirical benchmark study | Rapid growth in agent task horizons, with external-validity caveats. |
| Jimenez et al. (2024), *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* | ICLR 2024; arXiv:2310.06770 | Benchmark paper | Real-world issue resolution as a measure of increasingly autonomous software engineering. |
| Becker et al. (2025), *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity* | arXiv:2507.09089 | Randomized controlled trial | Counterweight to unconditional productivity claims. |
| Kretzer et al. (2025), *Closing the Loop between User Stories and GUI Prototypes* | CHI 2025, Article 879; DOI: 10.1145/3706598.3713932 | Empirical system paper | Closest direct comparison for detecting user-story fulfillment in GUI prototypes. |
| Berry, Kamsties, and Krieger (2003), *From Contract Drafting to Software Specification: Linguistic Sources of Ambiguity—A Handbook* | University of Waterloo technical report, version 1.0 | Technical report / handbook | Linguistic sources of ambiguity in requirements. |
| Gervasi, Ferrari, Zowghi, and Spoletini (2019), *Ambiguity in Requirements Engineering: Towards a Unifying Framework* | LNCS 11865, pp. 191–210; DOI: 10.1007/978-3-030-30985-5_12 | Book chapter | Requirements-ambiguity taxonomy and synthesis. |
| Cleland-Huang et al. (2014), *Software Traceability: Trends and Future Directions* | FOSE 2014; DOI: 10.1145/2593882.2593891 | Research agenda / review | Trace links between requirements and heterogeneous artifacts. |
| Nass, Alégroth, and Feldt (2021), *Why Many Challenges with GUI Test Automation (Will) Remain* | Information and Software Technology; DOI: 10.1016/j.infsof.2021.106625 | Empirical/review paper | Stateful and practical limitations of GUI automation. |
| Massenon, Gambo, and Khan (2026), *Toward an Automated Cross-Multimodal Verification of Mobile App Bug Fixes* | Information and Software Technology 191, 107996; DOI: 10.1016/j.infsof.2025.107996 | Empirical method | Related multimodal software-verification setting. The final issue year is 2026. |
| Deng et al. (2023), *Mind2Web: Towards a Generalist Agent for the Web* | NeurIPS 2023; arXiv:2306.06070 | Dataset/benchmark paper | Source and limitations of ordered web trajectories. |
| Rawles et al. (2023), *Android in the Wild* | NeurIPS 2023; arXiv:2307.10088 | Dataset paper | Related mobile trajectory data. |
| Cheng et al. (2024), *SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents* | ACL 2024; DOI: 10.18653/v1/2024.acl-long.505 | Method paper | GUI grounding and future region-level evidence. |
| Ferrari, Spagnolo, and Gnesi (2017), *PURE: A Dataset of Public Requirements Documents* | IEEE RE 2017; DOI: 10.1109/RE.2017.29; dataset DOI: 10.5281/zenodo.1414117 | Dataset paper and release | External structured requirements and document-context challenges. |
| Hendrickx et al. (2024), *Machine Learning with a Reject Option: A Survey* | Machine Learning 113, pp. 3073–3110; DOI: 10.1007/s10994-024-06534-x | Survey | Conceptual basis for abstention/reject options. Prefer this final version over the 2021 preprint. |
| Wen et al. (2025), *Know Your Limits: A Survey of Abstention in Large Language Models* | TACL 13, pp. 529–556; DOI: 10.1162/tacl_a_00754 | Survey | LLM-specific uncertainty and abstention framing. Prefer this final version over the 2024 preprint. |
| Yang et al. (2023), *Set-of-Mark Prompting Unleashes Extraordinary Visual Grounding in GPT-4V* | arXiv:2310.11441 | Method paper | Design inspiration for candidate-mark grounding; not an exact reproduction. |
| Zheng et al. (2024), *SeeAct: GPT-4V(ision) is a Generalist Web Agent, if Grounded* | ICML 2024, PMLR 235 | Method paper | Evidence that Set-of-Mark is not universally effective for web grounding. |
| Gou et al. (2025), *UGround: Universal Visual Grounding for GUI Agents* | ICLR 2025 | Method paper | Specialized trained GUI grounding alternative. |
| TUM CIT, *Thesis and Completing your Studies in Informatics* | Official TUM web page | Regulation/guidance | Deadline, portal, cover, title-page, and personal-data requirements. |
| TUM ProLehre, *Use AI wisely* | Official TUM web page | Institutional guidance | Permission and disclosure requirements for AI aids. |

The detailed correction list and chapter-by-chapter source role are maintained in [`thesis_structure_and_bibliography_audit_2026-07-21.md`](thesis_structure_and_bibliography_audit_2026-07-21.md). Before transfer to the final bibliography, verify complete author lists, capitalization, page ranges, DOI, and venue against the publisher or official proceedings page.

## 9. Reporting Rules for the Thesis

Every quantitative table must state:

- benchmark version or commit;
- included flows and item count;
- number of predictions and coverage;
- model and prompt version;
- claim-decomposition and aggregation policy;
- evidence strategy and top-k;
- API failures and fallbacks;
- whether labels were blinded, independently reviewed, or post-hoc.

Every interpretation must obey these boundaries:

- Visible UI evidence can support visible UI claims.
- Absence from a finite screenshot flow does not prove global absence.
- Missing evidence is not automatically `NOT_FULFILLED`.
- Forms and action controls do not prove successful or correct result states.
- Screenshots do not prove backend correctness, security, external delivery, long-term persistence, completeness, or real-world availability unless a visible proxy is explicitly what the requirement asks for.
- Evidence-first verification is not claimed to outperform whole-flow verification unless the final controlled experiment demonstrates it.
