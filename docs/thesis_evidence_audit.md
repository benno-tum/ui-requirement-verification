# Thesis Evidence Audit

Working title: **Automated UI Requirement Verification from Ordered Screenshot Sequences**

Audit date: **15 July 2026**

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
167 passed
```

This was checked on 15 July 2026 with `python -m pytest -q`. The test result supports the claim that the checked-in implementation is internally consistent and runnable. It does not establish scientific validity, model reliability, or external generalization.

The implemented evidence granularity is predominantly **screenshot-step-level**. Bounding boxes exist in parts of the schema and in isolated demonstrations, but localization is not a stable, systematically annotated, or evaluated pipeline contribution. The thesis must either add a proper bounding-box evaluation or remove bounding boxes from the final contribution claims.

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

- 29 verification items;
- 5 marked accepted and 24 marked `needs_review`;
- 27 annotations attributed to `codex_draft` and 2 to Benno;
- 25 `FULFILLED`, 3 `PARTIALLY_FULFILLED`, and 1 `ABSTAIN` draft labels.

Most Split/Merge annotations state that the preliminary model verdict was not inspected before drafting. This reduces direct prediction leakage, but the annotations still require independent human review. The current quantitative results are suitable only for an exploratory subsection or appendix.

Current Mashboot snapshot:

- 11 verification items;
- all 11 marked `needs_review`;
- all 11 attributed to `codex_draft`;
- the annotation notes explicitly state that the pipeline run had already been inspected.

The Mashboot labels are post-hoc and cannot serve as blinded gold. The preliminary result of 81.8% accuracy and 0.625 macro-F1 may be used to guide review, but it must not appear as headline evidence of generalization.

## 4. Controlled Preliminary Results

The only denominator-compatible model comparison currently available covers flows 01–10 and **201/201 predictions**. These results are preliminary because flows 11–13 are not present in every configuration and the final experiment manifest is not frozen.

| Configuration | Items / flows | Prompt and evidence strategy | Accuracy | Macro-F1 | False fulfillment | Coverage | Estimated cost |
|---|---|---|---:|---:|---:|---:|---:|
| Gemini 2.5 Flash Lite whole-flow | 201 / 01–10 | One call per flow; requirements treated as single claims; original screenshots | 76.1% | 0.480 | 12.4% | 100% | $0.0138 |
| Gemini 3.1 Pro whole-flow | 201 / 01–10 | One call per flow; requirements treated as single claims; original screenshots | 81.1% | 0.573 | 9.9% | 100% | $0.8401 |
| Gemini 2.5 Flash Lite batched top-k | 201 / 01–10 | Gated claim decomposition; lexical top-3; batched image verification | 75.1% | 0.387 | 21.5% | 100% | $0.0221 |
| Deterministic evidence-first baseline | 201 / 01–10 | Gated claims; lexical top-3; deterministic per-claim verification | 20.4% | 0.136 | 45.5% | 100% | No model API |

Whole-flow values come from the `comparison` records in:

- `data/generated/all_in_one_verification_runs/*_gemini_25_flash_lite_single_call_requirements_as_claims.json`
- `data/generated/all_in_one_verification_runs/*_gemini_31_pro_single_call_requirements_as_claims.json`
- `data/generated/all_in_one_verification_runs/single_call_gemini_flash_lite_vs_pro_flows_01_10_summary.json`

Batched top-k values were recomputed for flows 01–10 from the prediction JSON files in:

- `data/generated/verification_pipeline_runs/batched_topk_gemini_flash_lite_gated_realapi_20260709T144108/`

The corresponding evidence metrics are:

| Evidence metric | Batched top-k Flash Lite | Deterministic baseline |
|---|---:|---:|
| MRR | 0.582 | 0.159 |
| Hit@1 | 0.473 | 0.159 |
| Hit@3 | 0.657 | 0.159 |
| Recall@1 | 0.260 | 0.076 |
| Recall@3 | 0.485 | 0.076 |

Comparable evidence metrics are not yet available for the whole-flow files because their stored comparison format and evidence indexing are not accepted directly by the common evaluator. They must not be shown as absent or zero; they are currently **not computed in a comparable way**.

### 4.1 Interpretation Allowed by the Data

The controlled comparison supports the following preliminary statements:

- Gemini 3.1 Pro has the highest label accuracy and macro-F1 on the 201-item subset, but its recorded cost is roughly 61 times the Flash Lite whole-flow cost.
- Flash Lite whole-flow and batched top-k have similar accuracy, but the current batched top-k configuration has lower macro-F1 and a higher false-fulfillment rate.
- Therefore, the current results do **not** show that evidence-first top-k verification reduces unsafe fulfilled predictions. Its demonstrated benefit is explicit step-level traceability and measurable evidence retrieval, not superior label safety.
- The deterministic baseline is not competitive. It abstains heavily and still produces a high fraction of false fulfilled decisions among the few fulfilled predictions it emits.
- Accuracy alone is misleading because two thirds of the current benchmark is `FULFILLED` and only eight items are `NOT_FULFILLED`. Macro-F1 and per-class results must be reported alongside accuracy.

## 5. Historical and Inconsistent Artifacts

The following values are useful as history but must not be copied into the final result table:

| Historical value | Why it is not a current headline result |
|---|---|
| 169/259 = 65.3% | Assembled from the then-current run per flow, including API fallbacks and an older 259-item gold snapshot. |
| 173/258 = 67.1% | Mixed per-flow configurations selected for qualitative error analysis rather than a controlled experiment. |
| 48.6% Gemini diagnosis and 26.6% deterministic diagnosis | Only 173 predictions were present while the evaluator scored 259 gold items; missing predictions became abstentions. |
| 31.8% batched top-k in the stored `metrics.json` | The evaluator used all 258 gold items although only flows 01–10 and 201 predictions were present, producing 57 artificial missing predictions. |
| 201 accepted / 57 needs review | Outdated. The current Mind2Web files contain 258 accepted items. |
| 171/45/33/9 or 159/56/31/12 label distributions | Earlier benchmark snapshots. The current distribution is 172/45/33/8. |
| 142 candidate requirements | Combines 100 Mind2Web candidates with 42 committed PURE candidates. |

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
- Choose final configurations and run all of them over flows 01–13.
- Store a run manifest containing model identifier, date, prompt version, claim policy, retrieval strategy, top-k, image limits, aggregation method, retries, fallbacks, runtime, tokens, image count, and cost.
- Recompute every table from the frozen manifest rather than copying summary files by hand.
- Add an independent second review for at least a stratified sample covering every label and the main ambiguity categories; report agreement and adjudication.
- Produce comparable evidence metrics for the whole-flow and top-k variants.
- Run and report the no-decomposition, all-screenshots versus top-k, and aggregation ablations.
- Select and freeze 3–5 qualitative cases with requirement text, gold label, prediction, evidence steps, and a short error category.
- Add confidence intervals or bootstrap intervals for the primary label and safety metrics.
- Document Mind2Web/PURE licenses and specify which derived artifacts can be released.
- Decide whether bounding boxes are evaluated or removed from the contribution list.

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
| Cleland-Huang et al. (2014), *Software Traceability: Trends and Future Directions* | FOSE 2014; DOI: 10.1145/2593882.2593891 | Research agenda / review | Trace links between requirements and heterogeneous artifacts. |
| Nass, Alégroth, and Feldt (2021), *Why Many Challenges with GUI Test Automation (Will) Remain* | Information and Software Technology; DOI: 10.1016/j.infsof.2021.106625 | Empirical/review paper | Stateful and practical limitations of GUI automation. |
| Massenon et al. (2025), *Toward an Automated Cross-Multimodal Verification of Mobile App Bug Fixes* | Information and Software Technology; DOI: 10.1016/j.infsof.2025.107996 | Empirical method | Related multimodal software-verification setting. |
| Deng et al. (2023), *Mind2Web: Towards a Generalist Agent for the Web* | NeurIPS 2023; arXiv:2306.06070 | Dataset/benchmark paper | Source and limitations of ordered web trajectories. |
| Rawles et al. (2023), *Android in the Wild* | NeurIPS 2023; arXiv:2307.10088 | Dataset paper | Related mobile trajectory data. |
| Cheng et al. (2024), *SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents* | ACL 2024; DOI: 10.18653/v1/2024.acl-long.505 | Method paper | GUI grounding and future region-level evidence. |
| Ferrari, Spagnolo, and Gnesi (2017), *PURE: A Dataset of Public Requirements Documents* | IEEE RE 2017; DOI: 10.1109/RE.2017.29 | Dataset paper | External structured requirements and document-context challenges. |
| Hendrickx et al. (2021), *Machine Learning with a Reject Option: A Survey* | arXiv:2107.11277 | Survey | Conceptual basis for abstention/reject options. |
| Wen et al. (2024), *Know Your Limits: A Survey of Abstention in Large Language Models* | arXiv:2407.18418 | Survey | LLM-specific uncertainty and abstention framing. |
| TUM CIT, *Thesis and Completing your Studies in Informatics* | Official TUM web page | Regulation/guidance | Deadline, portal, cover, title-page, and personal-data requirements. |
| TUM ProLehre, *Use AI wisely* | Official TUM web page | Institutional guidance | Permission and disclosure requirements for AI aids. |

Before transfer to the final bibliography, verify author spelling, final publication year, title capitalization, DOI, and venue against the publisher or proceedings page.

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
