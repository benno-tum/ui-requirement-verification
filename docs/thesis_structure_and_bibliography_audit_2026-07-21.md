# Thesis Structure and Bibliography Audit

Working title: **Automated UI Requirement Verification from Ordered Screenshot Sequences**

Snapshot date: **21 July 2026**

This document is the recommended structural roadmap for the thesis. It reconciles the registered proposal, the implemented repository, the available experimental artifacts, the accessible thesis-planning task history, and the structural example in `Bachelor_thesis-1.pdf`. Quantitative claims remain governed by [`thesis_evidence_audit.md`](thesis_evidence_audit.md).

## 1. Structural Recommendation

Use **eight core chapters** and aim for approximately **42 pages of core text**. A reasonable planning interval is **40 ± 5 pages**, excluding front matter, bibliography, and appendices, subject to confirmation with the supervisor.

| Part | Target pages | Main purpose |
|---|---:|---|
| 1 Introduction | 4 | Motivation, problem, gap, research questions, contributions, and scope. |
| 2 Foundations and Related Work | 6 | Requirements, traceability, GUI verification, multimodal agents, grounding, and abstention. |
| 3 Research Design and Problem Formulation | 4 | Research design, formal task, labels, claims, evidence, and the visible/hidden boundary. |
| 4 Verification Approach and Implementation | 7 | Implemented pipeline, design choices, grounding, workbench, and reproducibility. |
| 5 Benchmark Construction and Annotation | 5 | Mind2Web-derived benchmark, review process, statistics, contrastive items, and exploratory PURE material. |
| 6 Evaluation | 10 | Experimental design, metrics, main results, evidence analysis, ablations, efficiency, and errors. |
| 7 Discussion | 4 | Direct research-question answers, interpretation, implications, threats, and limitations. |
| 8 Conclusion | 2 | Contributions, concise answers, and future work. |
| **Total core text** | **42** | Excludes abstracts, lists, bibliography, and appendices. |

This structure is preferable to the previous nine-chapter plan for three reasons:

1. It combines evaluation design and results, so each result appears directly beside its configuration, metric, and denominator.
2. It integrates the small standalone problem-definition chapter into a broader research-design chapter, avoiding fragmentation while retaining the formal task definition.
3. It keeps benchmark construction separate because the reviewed requirement/evidence dataset is a thesis contribution, not merely experimental setup.

## 2. Recommended Table of Contents

### Front Matter

- Title page with English and German titles.
- Declaration of originality and the approved AI-use disclosure.
- Acknowledgements, if desired.
- Abstract.
- German summary (`Zusammenfassung`).
- Table of contents.
- Lists of figures, tables, and abbreviations when long enough to justify them.

Front matter and bibliography do not count toward the 42-page core target.

### 1 Introduction

#### 1.1 Motivation

Start from the rapid progress of coding agents. Keep the argument deliberately qualified: agent task capabilities and practical adoption have advanced quickly, but observed end-to-end productivity effects remain dependent on task, developer, and workflow. As candidate implementations become cheaper to produce, precise requirements and reliable verification become relatively more important.

Use Kwa et al. (2025) for measured task-horizon growth, SWE-bench for the move from code completion toward repository-level issue resolution, and Becker et al. (2025) as the counterweight to unconditional productivity claims.

#### 1.2 Problem Statement and Research Gap

Explain the mismatch between textual requirements and visual, stateful UI behaviour. One screenshot rarely establishes a multi-step requirement, while a finite screenshot flow remains an incomplete observation of the system. Existing UI-agent work primarily studies action selection or element grounding; existing traceability work does not solve screenshot-flow verification; and the closest GUI/user-story and cross-modal bug-fix work does not provide the same four-label evidence contract over ordered flows.

#### 1.3 Objective and Research Questions

Use these formulations:

**RQ1:** How accurately can multimodal models apply a provided, application-specific verification label schema to UI-observable textual requirements using ordered screenshot flows?

**RQ2:** How do claim decomposition and screenshot selection affect label accuracy, evidence traceability, and cost relative to direct whole-flow verification?

**RQ3:** Which requirement and evidence patterns cause verification errors, abstentions, or unsafe `FULFILLED` predictions?

RQ2 is intentionally comparative and neutral. RQ3 is descriptive and diagnostic rather than a causal abstention experiment. PURE remains an exploratory subsection or appendix rather than a numbered research question.

#### 1.4 Contributions

Claim only contributions supported by the final evidence:

1. A formal task and conservative evidence policy for screenshot-based UI requirement verification.
2. An implemented modular verifier and annotation workbench.
3. A reviewed Mind2Web-derived benchmark with labels, claims, screenshot-step evidence, rationales, and contrastive items.
4. A controlled evaluation framework covering label quality, unsafe positive predictions, abstention, traceability, and efficiency.
5. An empirical error analysis of partial evidence, late states, hidden outcomes, and universal or comparative wording.

Bounding-box localization becomes a sixth contribution only if the current regions receive an independent human evaluation with a frozen protocol. Otherwise it is an implemented extension and exploratory analysis, not a validated contribution.

#### 1.5 Scope and Thesis Organization

State that the thesis assesses what ordered screenshots visibly support. It does not establish backend correctness, persistence, security, completeness, external effects, or every reachable UI state. End with one short paragraph outlining Chapters 2–8.

### 2 Foundations and Related Work

#### 2.1 Requirements Quality, Ambiguity, and Traceability

Define ambiguity, compound obligations, context dependence, and trace links. Use Berry, Kamsties, and Krieger (2003), Gervasi et al. (2019), and Cleland-Huang et al. (2014). The synthesis point is that verification requires a documented link between a textual obligation and heterogeneous evidence.

#### 2.2 GUI Verification and Ordered Interaction State

Explain why GUI behaviour is stateful, why action controls do not prove outcomes, and why traditional automated GUI testing requires executable systems, selectors, or oracles. Use Nass, Alégroth, and Feldt (2021). Distinguish screenshot verification from executable end-to-end testing.

#### 2.3 Multimodal UI Agents and Interaction Datasets

Position Mind2Web, Android in the Wild, and related web-agent work. Make clear that this thesis repurposes trajectories as ordered observations; it does not evaluate action prediction.

#### 2.4 Requirement-to-UI and Cross-Modal Verification

Treat Kretzer et al. (2025) as the closest requirements-to-GUI prototype paper and Massenon, Gambo, and Khan (2026) as related cross-modal software verification. Compare their input artifacts, decision targets, evidence outputs, and evaluation settings with this thesis.

#### 2.5 Visual Grounding and Evidence Localization

Use SeeClick for GUI-specific grounding. Discuss Set-of-Mark, SeeAct, and UGround only if region grounding remains in the final thesis. Candidate-mark grounding in this repository is inspired by, but is not an exact reproduction of, Set-of-Mark.

#### 2.6 Abstention and Selective Prediction

Use the final journal version of Hendrickx et al. (2024) and the final TACL version of Wen et al. (2025). Explain `ABSTAIN` as a task label for insufficient visible evidence, not as a generic API failure or missing prediction.

#### 2.7 Gap Synthesis

End the chapter with a compact comparison table. Suggested columns are input artifact, temporal order, requirement decomposition, evidence output, abstention, and evaluation target. The final paragraph should derive the thesis design rather than merely list papers.

### 3 Research Design and Problem Formulation

#### 3.1 Research Design

Describe the work as a design-and-evaluation study: construct an artifact, construct and review an evaluation benchmark, compare controlled configurations, and analyse errors. Present the proposal's expectation that evidence discipline may reduce false fulfillment as a hypothesis, not a guaranteed outcome.

#### 3.2 Formal Verification Task

Define an ordered screenshot flow, requirement, atomic claim, visible evidence, and verifier output. State the distinction between screenshot order and completeness of observation.

#### 3.3 UI Evaluability and Requirement Labels

Define `UI_VERIFIABLE`, `PARTIALLY_UI_VERIFIABLE`, and `NOT_UI_VERIFIABLE` separately from `FULFILLED`, `PARTIALLY_FULFILLED`, `NOT_FULFILLED`, and `ABSTAIN`. Explain why evaluability and fulfillment answer different questions.

#### 3.4 Claim Statuses, Evidence, and Aggregation

Document the exact claim-status vocabulary used by the frozen implementation and annotation schema. Resolve the current written-schema drift around `SUPPORTED_WITH_CAVEAT` and `PARTIALLY_SUPPORTED` before submission. Define the deterministic safety rules for requirement aggregation.

#### 3.5 Epistemic Boundary

Formalize three central rules:

1. `FULFILLED` requires visible support for every central observable claim.
2. Missing evidence is not by itself `NOT_FULFILLED`.
3. A hidden or external outcome remains partial or undecidable unless the visible proxy is exactly what the requirement asks for.

Use Amtrak as the positive running example and a late-state cart/checkout or hidden-result case as the contrasting example.

### 4 Verification Approach and Implementation

#### 4.1 Architecture Overview

Present one pipeline figure from screenshot flow and requirement to claims, evidence selection, multimodal decisions, aggregation, and review output.

#### 4.2 Ordered Screen Representation

Explain step indexing, image variants, extracted text/metadata, caching, and the preservation of sequence order. Mention that contiguous repository indices validate internal consistency but do not prove that the upstream trajectory contains every meaningful state.

#### 4.3 Requirement Understanding and Claim Policy

Describe UI-evaluability prediction, optional claim decomposition, and the distinction between provided benchmark claims and model-generated claims. Never call a provided-claim run a realistic end-to-end decomposition result.

#### 4.4 Evidence Selection

Describe all-screenshot and lexical top-k strategies, batching, image limits, and the risk of missing decisive late states. Explain the difference between evidence retrieval and evidence generation in whole-flow outputs.

#### 4.5 Multimodal Claim Verification

Describe the prompt contract, visible-evidence discipline, uncertainty reasons, model output normalization, retries, and fallbacks. Report exact prompt and model identifiers in the evaluation manifest rather than relying on marketing-family names.

#### 4.6 Requirement Aggregation and Safety Gates

Describe deterministic aggregation over claim statuses. Semantic aggregation remains an ablation unless it is frozen and evaluated over identical claim outputs with the same safety gates.

#### 4.7 Candidate-Mark Grounding

Describe OmniParser/OCR candidate generation and model mark selection as a post-hoc or joint localization module. Separate candidate coverage, mark-selection accuracy, and end-to-end label quality. The July 21 regions are generated outputs, not localization ground truth.

#### 4.8 Annotation Workbench and Reproducibility

Describe review interfaces, audit queues, run summaries, evaluators, and manifests. Use the current test result—**203 passed on 21 July 2026**—only as implementation validation, not as scientific performance evidence.

### 5 Benchmark Construction and Annotation

#### 5.1 Data Source and Flow Selection

Describe the selection of 13 flows from the locally processed Mind2Web material and how ordered screenshots are derived. Include the upstream dataset's scope and license constraints.

#### 5.2 Requirement Construction Funnel

Explain harvested, candidate, reviewed source, contrastive, and verification-gold stages. Automatically generated or rewritten text is never ground truth before human review.

#### 5.3 Annotation Schema and Review Protocol

Describe requirement labels, UI evaluability, claims, claim statuses, evidence steps, rationales, uncertainty reasons, and acceptance status. “Accepted” currently means primary-author review, not independent agreement.

#### 5.4 Benchmark Statistics and Temporal Properties

Report the frozen counts and label distribution. Include sequence-specific statistics because they justify the ordered-flow formulation: multi-screen requirements, multi-step evidence, sequence cues, and the location of decisive late evidence.

#### 5.5 Contrastive Requirements

Explain why contrastive items reduce an otherwise positive-heavy benchmark and how they were reviewed. Report results separately for source and contrastive requirements in the final analysis.

#### 5.6 Exploratory PURE Material

Use PURE to study extraction, contextualization, compound requirements, and the visible/hidden boundary. Clearly distinguish intended-design figures from observations of a running implementation. Split/Merge and Mashboot remain exploratory because of provenance, review, and post-hoc-label concerns.

#### 5.7 Quality and Release Boundaries

Report the independent second-review protocol, agreement/adjudication, benchmark checksum, and licensing/release statement. If these are not completed, retain them as explicit validity limitations.

### 6 Evaluation

#### 6.1 Evaluation Questions and Frozen Manifest

Map each experiment and metric to an RQ. Every table must state benchmark version, included flows, item and prediction counts, coverage, model, prompt, claim policy, screenshot strategy, aggregation, failures, and cost basis.

#### 6.2 Compared Configurations

At minimum distinguish:

1. Whole-flow stronger-model verification with provided claims.
2. Whole-flow or joint Flash-Lite verification with provided claims.
3. Realistic raw-requirement top-k verification without decomposition.
4. Deterministic baseline on the same frozen benchmark.
5. Controlled single-factor ablations for screenshot selection, claim policy, ordering, and aggregation.

The first three complete runs currently differ in several factors and must not be presented as a clean decomposition or retrieval ablation.

#### 6.3 Metrics and Statistical Analysis

Define accuracy, macro-F1, per-class scores, false-fulfillment rate, abstention rate, prediction coverage, evidence hit@k, recall@k, MRR, claim matching, runtime, failures, and estimated cost. Add confidence intervals to primary metrics. Treat flows as clustered observations when interpreting uncertainty; 258 requirements from 13 flows are not 258 fully independent systems.

#### 6.4 Main Requirement-Label Results

Use the final frozen 258-item results, confusion matrices, and per-class scores. Lead with macro-F1 and false fulfillment rather than accuracy alone because the benchmark is label-imbalanced.

#### 6.5 Evidence Traceability Results

Compare evidence hit@k, recall@k, and MRR only when evidence output formats and gold denominators are compatible. Distinguish retrieving a relevant step from selecting a sufficient set of steps for a multi-state claim.

#### 6.6 Controlled Ablations

Prioritize these experiments:

1. All screenshots versus top-k with the same model, claims, prompt, and aggregation.
2. Provided or frozen claims versus raw requirements with every other factor held constant.
3. Ordered versus shuffled screenshots.
4. Deterministic versus semantic aggregation over frozen claim outputs.
5. Candidate-mark grounding on versus off, only if grounding remains a contribution.

#### 6.7 UI-Evaluability and Grounding Analyses

Report independent UI-evaluability agreement separately from fulfillment accuracy. Include region-level results only after blind or prediction-independent human review; generated box counts and geometric validity alone do not establish relevance or sufficiency.

#### 6.8 Efficiency and Reliability

Report API calls, images, tokens where available, runtime, retries, fallbacks, and dated pricing assumptions. Separate estimated cost from billed cost.

#### 6.9 Error Analysis and Qualitative Cases

Use 3–5 frozen cases covering:

- over-fulfillment from partial visible evidence;
- hidden or external outcomes;
- universal or comparative wording;
- missed late cart, checkout, result, or summary states;
- an accurate, fully traceable positive such as Amtrak.

### 7 Discussion

#### 7.1 Answers to the Research Questions

Answer RQ1–RQ3 directly and in order. Separate measured findings from interpretation.

#### 7.2 What Evidence-First Verification Does and Does Not Provide

Discuss traceability and failure localization even if the final evidence-first configuration does not win on label metrics. Do not turn “inspectable” into “more accurate” without evidence.

#### 7.3 Implications for Requirements Engineering and Verification

Return to the introduction's bottleneck argument: cheaper implementation increases the value of precise intent and reliable checking, but screenshot verification is only one partial oracle. Discuss how conservative visible-evidence contracts could assist, rather than replace, human review and executable tests.

#### 7.4 Threats to Validity

Organize threats into construct, internal, external, and reliability validity. Required topics are generated requirements, single-author gold, class imbalance, flow clustering, model/prompt drift, incomplete observations, provided claims, PURE provenance, and licensing.

#### 7.5 Limitations and Future Work

Keep future work concrete: independent review, larger heterogeneous flows, calibrated uncertainty, better temporal retrieval, reproducible model manifests, and evaluated region grounding.

### 8 Conclusion

#### 8.1 Summary of Contributions

Summarize only completed contributions.

#### 8.2 Final Answers

Give one compact paragraph answering the main research questions without repeating all result tables.

#### 8.3 Outlook

End with the broader point that useful automated verification must state what its evidence can and cannot establish.

## 3. Research-Question-to-Evidence Map

| RQ | Primary thesis sections | Required evidence | Current readiness |
|---|---|---|---|
| RQ1: supplied label-schema accuracy | 6.2–6.4, 7.1 | Frozen 258-item runs from at least two models, macro-F1, per-label results, confusion matrices, false fulfillment, inter-model agreement, and confidence intervals | Full-coverage Gemini runs exist; the final matched two-model manifest and intervals remain. |
| RQ2: decomposition and screenshot selection | 6.2, 6.5–6.8, 7.2 | Factor-controlled raw/gated-claims by all/top-k matrix, evidence metrics, token usage, runtime, and cost | Final controlled runs are prepared but not yet executed. |
| RQ3: failure patterns | 6.9, 7.1–7.4 | Predefined taxonomy, frozen qualitative cases, category-level counts, abstention reasons, and unsafe-`FULFILLED` analysis | Strong historical categories exist; final examples and category protocol remain. |

## 4. Alignment with the Registered Proposal

| Proposal commitment | Thesis location | Adaptation required by current evidence |
|---|---|---|
| Verify textual requirements from ordered screenshots with four labels and evidence | Chapters 3 and 4 | Retain exactly; make screenshot-step evidence the mature level. |
| Build a small high-quality trajectory benchmark | Chapter 5 | Retain and document the harvested-to-gold funnel, contrastive items, and single-author-review limitation. |
| Compare with structured PURE requirements | Sections 5.6 and 7.1 or appendix | Retain as exploratory document-to-UI consistency, not equivalent ordered-flow evidence. |
| Test whether evidence discipline reduces false fulfillment | Sections 6.4–6.6 and 7.2 | Preserve as a hypothesis. Current results do not justify claiming the outcome in advance. |
| Retrieve relevant screenshots before verification | Sections 4.4 and 6.5–6.6 | Compare with whole-flow input under controlled factors; analyze missed late states. |
| Produce screenshot IDs and bounding boxes | Sections 4.7 and 6.7 | Screenshot IDs are mature. Bounding boxes remain conditional on human evaluation. |
| Evaluate whole-flow versus evidence-first and other ablations | Section 6.6 | Add the missing single-factor runs; do not infer ablation effects from mixed configurations. |
| Exclude hidden backend, security, and performance truth | Sections 1.5, 3.5, and 7.4 | Retain as a central epistemic boundary throughout the thesis. |

The proposed architecture and main problem remain intact. The most important adaptation is rhetorical: the thesis evaluates whether evidence discipline improves safety and traceability; it does not assume that it necessarily improves classification performance.

## 5. Lessons from the Colleague Thesis

The supplied chair thesis is a useful structural precedent, not a scientific source. It contains 72 PDF pages, approximately 52 pages of numbered core text, and eight main chapters: Introduction; Background and Related Work; Methodology; Theoretical Framework; System Design and Implementation; Evaluation; Discussion; and Conclusion. Its bibliography spans approximately eight pages.

Transfer these patterns:

- separate foundations, methodology/problem formulation, implementation, evaluation, discussion, and conclusion;
- state research questions early and answer them explicitly near the end;
- keep implementation detail subordinate to research questions;
- give evaluation the largest share of core pages;
- include both English and German summaries and clean front matter.

Do not copy its exact page count, reference count, chapter titles, or prose. This thesis needs a dedicated benchmark-construction chapter because annotation and evidence policy are central contributions. The colleague thesis must not be cited as evidence for a scientific claim.

## 6. Current Evidence That Fits the Structure

The current main benchmark contains 13 flows, 258 accepted verification items, and 541 claims. The labels are 172 `FULFILLED`, 45 `PARTIALLY_FULFILLED`, 33 `ABSTAIN`, and 8 `NOT_FULFILLED`. Acceptance represents primary-author review.

The most current complete model results are:

| Configuration | Items / coverage | Accuracy | Macro-F1 | False fulfillment | Abstain rate | Evidence MRR | Hit@1 / Hit@3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Gemini 3.1 Pro, all screenshots, provided claims | 258 / 100% | 78.3% | 0.560 | 7.6% | 6.2% | 0.899 | 0.884 / 0.915 |
| Gemini 3.1 Flash-Lite, joint verification and candidate grounding, provided claims | 258 / 100% | 76.7% | 0.528 | 12.4% | 7.4% | 0.808 | 0.795 / 0.822 |
| Gemini 3.1 Flash-Lite, lexical top-4, raw requirements, no decomposition | 258 / 100% | 72.1% | 0.449 | 10.5% | 27.1% | 0.606 | 0.593 / 0.620 |

These results are denominator-compatible but still preliminary. They support a current-status table, not a clean causal claim, because the configurations vary in model strength, screenshot selection, claim policy, execution grouping, and grounding. The older 201-item table should move to experiment history or the appendix once the 258-item manifest is frozen.

The July 21 candidate-grounding run contains 541 claim decisions and 588 stored boxes/evidence records across 13 model calls at an estimated cost of $0.484779. This demonstrates pipeline execution and region coverage, not localization accuracy. Human relevance and sufficiency judgments remain necessary.

The realistic raw-requirement top-k run produced 258 predictions with no final fallbacks, 29 model calls, 252 stored boxes, and an estimated cost of $0.561202. Its independently predicted UI-evaluability labels have 79.5% raw agreement with gold, macro-F1 0.420, and Cohen's kappa 0.325; the model almost never recognizes the small non-UI-verifiable class. Keep this as an auxiliary analysis, not a replacement for requirement verification.

PURE currently provides 31 accepted Split/Merge items with 78 claims and 11 accepted Mashboot items. Most provenance remains Codex-draft, and Mashboot annotations were drafted after predictions had been inspected. “Accepted” therefore does not make these blinded or independently adjudicated gold. Keep them exploratory.

## 7. Bibliography Audit

### 7.1 Essential Sources by Thesis Claim

- **Agent task capability:** Kwa et al., *Measuring AI Ability to Complete Long Tasks*. 2025, arXiv:2503.14499. Use with external-validity caveats.
- **Repository-level software-agent evaluation:** Jimenez et al., *SWE-bench*. ICLR 2024, arXiv:2310.06770. This is benchmark evidence, not direct productivity evidence.
- **Mixed productivity effects:** Becker et al., *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*. 2025, arXiv:2507.09089, randomized controlled trial.
- **User stories checked against GUI prototypes:** Kretzer et al., *Closing the Loop between User Stories and GUI Prototypes*. CHI 2025, Article 879, DOI: 10.1145/3706598.3713932. This was missing from the earlier draft and is the closest related work.
- **Requirements ambiguity:** Berry, Kamsties, and Krieger, *From Contract Drafting to Software Specification*. University of Waterloo technical report, version 1.0, November 2003.
- **Unified ambiguity framework:** Gervasi, Ferrari, Zowghi, and Spoletini, *Ambiguity in Requirements Engineering*. LNCS 11865, 2019, pp. 191–210, DOI: 10.1007/978-3-030-30985-5_12.
- **Software traceability:** Cleland-Huang et al., *Software Traceability: Trends and Future Directions*. FOSE 2014, pp. 55–69, DOI: 10.1145/2593882.2593891.
- **GUI automation limitations:** Nass, Alégroth, and Feldt, *Why Many Challenges with GUI Test Automation (Will) Remain*. Information and Software Technology 138 (2021), 106625, DOI: 10.1016/j.infsof.2021.106625.
- **Cross-modal verification of software artifacts:** Massenon, Gambo, and Khan, *Toward an Automated Cross-Multimodal Verification of Mobile App Bug Fixes*. Information and Software Technology 191 (March 2026), 107996, DOI: 10.1016/j.infsof.2025.107996.
- **Source trajectory benchmark:** Deng et al., *Mind2Web*. NeurIPS 36 (2023). Use the official proceedings version.
- **Related mobile interaction data:** Rawles et al., *Android in the Wild*. NeurIPS 36 (2023). Related work only unless added to the benchmark.
- **GUI grounding:** Cheng et al., *SeeClick*. ACL 2024, pp. 9313–9332, DOI: 10.18653/v1/2024.acl-long.505.
- **Structured public requirements corpus:** Ferrari, Spagnolo, and Gnesi, *PURE*. IEEE RE 2017, pp. 502–505, DOI: 10.1109/RE.2017.29; dataset DOI: 10.5281/zenodo.1414117.
- **Reject option and selective prediction:** Hendrickx et al., *Machine Learning with a Reject Option: A Survey*. Machine Learning 113 (2024), pp. 3073–3110, DOI: 10.1007/s10994-024-06534-x.
- **LLM abstention:** Wen et al., *Know Your Limits*. Transactions of the ACL 13 (2025), pp. 529–556, DOI: 10.1162/tacl_a_00754.
- **Candidate-mark grounding, if retained:** Yang et al., *Set-of-Mark Prompting Unleashes Extraordinary Visual Grounding in GPT-4V*. 2023, arXiv:2310.11441.
- **Counterevidence to universal Set-of-Mark effectiveness:** Zheng et al., *SeeAct*. ICML 2024, PMLR 235. Prefer the final proceedings version.
- **Specialized GUI grounder, if retained:** Gou et al., *UGround*. ICLR 2025. Prefer the official proceedings version.

### 7.2 Corrections Required in Existing Thesis Files

1. Change Massenon et al. from **2025** to **2026** when citing the final journal issue. The DOI was assigned in 2025, but the final volume is March 2026.
2. Replace Hendrickx et al. (2021) arXiv metadata with the **2024 Machine Learning** version and DOI.
3. Replace Wen et al. (2024) arXiv metadata with the **2025 TACL** version and DOI.
4. Add Kretzer et al. (2025), which is in the proposal and is the closest direct requirements-to-GUI comparison.
5. Add Berry et al. (2003) and Gervasi et al. (2019) to the thesis bibliography if their ambiguity concepts remain in Chapter 2 or the label policy. They are currently mentioned only in the annotation guide.
6. If bounding boxes remain, replace SeeAct and UGround arXiv-only citations with their ICML 2024 and ICLR 2025 proceedings versions.
7. Do not treat SWE-bench performance as evidence of developer productivity. Pair capability evidence with the Becker randomized study.
8. Do not cite Android in the Wild as a dataset used by this thesis unless an actual AITW experiment is added.
9. Cite the PURE paper for corpus construction and the Zenodo record for the concrete released dataset/version.

### 7.3 Sources Still Needed Before Submission

- A dated official pricing source for every reported model-cost estimate, archived or recorded with the final run date.
- A precise Mind2Web license and derived-artifact-release statement.
- A precise PURE license/reuse statement for the selected documents and derived annotations.
- A methodological source for the final human-agreement protocol if Cohen's kappa, weighted kappa, or another statistic becomes a reported contribution.
- A statistical-method citation for the chosen confidence-interval or clustered-bootstrap procedure.
- Exact model documentation only where a model-specific capability or parameter is discussed; run manifests remain the primary source for the actual experimental configuration.

### 7.4 Citation Discipline

- Use author–year citations consistently in the prose.
- Prefer the publisher or official proceedings version over an arXiv version when a final version exists.
- Attach each citation to a specific claim; avoid paragraphs ending in a large undifferentiated citation cluster.
- Separate empirical evidence from motivation and from design inspiration.
- Cite datasets both for their original task and for limitations relevant to reuse.
- Never cite generated repository reports as independent scientific evidence. They are experimental artifacts and should instead be identified by run ID and manifest.

## 8. Immediate Writing Order

1. Freeze the chapter titles and research questions with the supervisor.
2. Write Chapter 3 first; it fixes the vocabulary used by every later chapter.
3. Write Chapter 5 from the reviewed benchmark and provenance records.
4. Write Chapter 4 from the implemented pipeline, omitting code-level chronology.
5. Complete the controlled runs and then write Chapter 6 from a frozen manifest.
6. Write Chapter 2 as a comparative synthesis around the gap identified in Chapter 1.
7. Rewrite the Introduction after the main result is stable.
8. Write Discussion and Conclusion last, with direct RQ answers.

This order minimizes rewriting because the abstract, introduction, and conclusion depend on the final evaluation outcome.
