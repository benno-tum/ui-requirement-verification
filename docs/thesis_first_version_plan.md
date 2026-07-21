# First Thesis Version Plan

Working title: **Automated UI Requirement Verification from Ordered Screenshot Sequences**

Examiner: Prof. Dr. Stefan Wagner

Supervisor: Mohamed Ben Salha
Registered timeframe: 2 April 2026 to 3 August 2026

This plan is the current writing roadmap. Quantitative sources, historical inconsistencies, and missing experiments are maintained in [`thesis_evidence_audit.md`](thesis_evidence_audit.md). Drafted prose is maintained in [`thesis_first_draft.md`](thesis_first_draft.md). The evidence audit, rather than older progress reports, is the source of truth for counts and preliminary metrics.

## 1. Thesis Position

The thesis studies whether textual UI requirements can be verified against ordered screenshot flows with explicit, inspectable evidence and principled uncertainty.

The main claim should be:

> UI requirement verification from screenshots is not only a label-prediction task. It is a traceability and uncertainty task. A verifier must connect each decision to visible states in an ordered flow and must preserve uncertainty when those states do not establish the requirement.

The thesis must not claim that screenshots prove hidden backend truth or that the current evidence-first pipeline already outperforms simpler multimodal prompting. The present controlled results show that evidence-first verification improves inspectability and makes retrieval measurable, but the current top-k configuration has worse macro-F1 and false fulfillment than the whole-flow baselines.

## 2. Scope and Formal Target

Plan for **40 ± 5 pages of core text**, excluding front matter, bibliography, and appendices. TUM CIT does not state one universal Informatics page count, and other TUM chairs publish different orientation values. Confirm the target with the supervisor.

The central TUM requirements to carry into the final template are:

- four-month processing period for a Bachelor's Thesis in Informatics;
- submission through the CIT Portal;
- no matriculation number or unrelated personal information on the cover;
- English and German title on the first page;
- examiner and supervisor names including academic titles;
- submission date;
- transparent declaration of permitted AI-tool use.

The thesis is written in academic English. Use author–year citations in Markdown and convert them consistently to the final LaTeX or Word citation style later.

## 3. Research Questions

**RQ1:** How accurately can multimodal models verify textual UI requirements from ordered screenshot flows?

**RQ2:** How does evidence-first verification affect label quality, false fulfillment, evidence traceability, and cost compared with whole-flow and deterministic baselines?

**RQ3:** Which requirement and evidence patterns cause the most frequent errors or abstentions?

**RQ4:** As an exploratory question, how well does the approach transfer to structured PURE requirements?

RQ2 is intentionally neutral. It tests whether the evidence-first architecture helps; it does not presuppose that it must outperform the whole-flow baseline.

## 4. Proposed Structure and Page Budget

| Section | Target pages | Purpose |
|---|---:|---|
| Abstract | 0.5–1 | Problem, method, dataset, main result, and limitation. |
| 1 Introduction | 3–4 | Motivation, research gap, RQs, contributions, and scope. |
| 2 Background and Related Work | 6–7 | Requirements ambiguity/traceability, GUI testing, UI agents/grounding, multimodal verification, abstention. |
| 3 Problem Definition | 3–4 | Formal input/output, evaluability, label policy, claims, evidence, and visible/hidden boundary. |
| 4 Approach | 6–7 | Screen understanding, claim handling, retrieval, screenshot verification, aggregation, and implementation. |
| 5 Dataset and Annotation | 4–5 | Mind2Web flows, construction pipeline, contrastive items, schema, review, and PURE. |
| 6 Evaluation Design | 3–4 | Configurations, RQs, metrics, experiment manifest, and analysis procedure. |
| 7 Results | 4–5 | Final controlled label, safety, evidence, cost, ablation, and error results. |
| 8 Discussion and Threats | 4–5 | Meaning, limitations, validity, generalization, and practical implications. |
| 9 Conclusion | 1.5–2 | Answer RQs, summarize contribution, and future work. |
| **Core text** | **35–44** | Final length depends on figures and final experiment breadth. |

## 5. Chapter Content

### 1 Introduction

Open with the rapid development of AI coding agents, but qualify the productivity claim. Agent capabilities and adoption have grown quickly, while measured end-to-end productivity remains task- and context-dependent. The argument is that cheaper candidate implementation increases the relative importance of expressing intent and verifying behavior.

Then establish:

- requirements are textual, but UI behavior is visual and state-based;
- many obligations span several screens;
- one observed flow is incomplete evidence about the entire system;
- unsafe over-fulfillment is more problematic than honest abstention;
- the thesis verifies visible UI contracts, not hidden backend properties.

End with the research questions and five contributions: problem formulation, prototype, reviewed benchmark, evaluation framework, and error analysis.

Status: a complete first version exists in `thesis_first_draft.md`.

### 2 Background and Related Work

Recommended subsections:

1. **Requirements ambiguity and traceability.** Explain compound, quantified, contextual, and hidden obligations. Introduce requirement-to-screenshot-step trace links.
2. **GUI testing and ordered interaction state.** Explain why UI behavior depends on state and why screenshots are weaker than executable tests.
3. **UI agents, datasets, and grounding.** Position Mind2Web, Android in the Wild, and SeeClick. Distinguish action prediction and element grounding from requirement verification.
4. **Multimodal software verification.** Position related screenshot/text verification work such as Massenon et al.
5. **Reject options and abstention.** Motivate `ABSTAIN` as a required output rather than a generic failure.

Every subsection should finish by stating what it contributes to the thesis design. Avoid a catalogue of papers without synthesis.

### 3 Problem Definition

Define:

- screenshot flow as an ordered sequence of visible UI states;
- requirement as a textual obligation;
- claim as an atomic semantic obligation derived from requirement text;
- evidence as one or more screenshot steps and an observation;
- UI evaluability separately from the final label;
- requirement labels and claim statuses;
- the conservative aggregation contract.

Use the Amtrak dining example to show a valid visible positive. Contrast it with route applicability or account-ownership wording to show how a hidden obligation changes the decision.

Important invariants:

- no `FULFILLED` without evidence for every core observable claim;
- missing evidence alone is not `NOT_FULFILLED`;
- forms and buttons do not prove correct result states;
- finite screenshot flows do not prove universal absence or completeness;
- visible proxies must be described as proxies.

### 4 Approach

Describe the implemented pipeline behavior, not source files:

1. Screen understanding preserves order and constructs cached text/metadata representations.
2. Requirement understanding estimates UI evaluability and optionally decomposes the requirement.
3. Evidence retrieval ranks candidate screenshot steps per claim.
4. Screenshot-grounded verification predicts claim status, evidence, uncertainty, and rationale.
5. Deterministic aggregation produces the final requirement decision.

Compare whole-flow and top-k execution. Explain the trade-off between complete context, visual attention, input cost, and retrieval failure. State that the current batched grouping may attach a large union of images even when retrieval is top-3 per claim.

Bounding boxes may be mentioned only as schema support or future work unless a final region-level experiment is added.

### 5 Dataset and Annotation Methodology

Current Mind2Web source-of-truth snapshot:

- 13 flows;
- 100 candidate requirements;
- 173 reviewed source requirements;
- 85 contrastive verification items;
- 258 accepted verification items;
- 541 gold claims;
- labels: 172 fulfilled, 45 partial, 33 abstain, and 8 not fulfilled.

Explain harvested, candidate, gold, contrastive, and verification-gold stages. Do not describe automatically generated requirements or intended labels as ground truth before review.

State explicitly that all 258 current Mind2Web items were reviewed by the primary author. “Accepted” is not inter-annotator agreement. Independent re-review remains required.

Treat PURE as exploratory:

- Split/Merge: 29 items, 5 accepted and 24 needing review;
- Mashboot: 11 post-hoc items, all needing review;
- suitable for contextualization and claim-decomposition discussion, not final generalization claims in the current state.

### 6 Evaluation Design

Primary metrics:

- accuracy and macro-F1;
- per-class precision, recall, and F1;
- confusion matrix;
- false-fulfillment rate;
- abstain rate and prediction coverage;
- evidence hit@k, recall@k, precision@k, and MRR;
- claim-match recall and claim-status macro-F1;
- runtime, tokens, images, fallbacks, and estimated cost.

Final configurations should include:

1. deterministic evidence-first baseline;
2. whole-flow Flash Lite baseline without claim decomposition;
3. whole-flow stronger-model baseline;
4. evidence-first top-k Flash Lite;
5. no-decomposition ablation;
6. all-screenshots versus top-k ablation;
7. aggregation-policy ablation.

Every configuration must run over the same frozen 258 items. Store exact model identifiers, prompt versions, evidence strategy, and failures in one run manifest.

### 7 Results

The current controlled preliminary comparison covers 201 items from flows 01–10:

| Configuration | Accuracy | Macro-F1 | False fulfillment |
|---|---:|---:|---:|
| Gemini Flash Lite whole-flow | 76.1% | 0.480 | 12.4% |
| Gemini 3.1 Pro whole-flow | 81.1% | 0.573 | 9.9% |
| Gemini Flash Lite batched top-k | 75.1% | 0.387 | 21.5% |
| Deterministic baseline | 20.4% | 0.136 | 45.5% |

These values are preliminary and must not be mixed with historical 13-flow current-run reports. The final chapter must replace or confirm them after controlled flows 11–13 runs.

Current evidence metrics are comparable only for batched top-k and deterministic outputs. Whole-flow evidence must be normalized and evaluated before the final table.

Planned results subsections:

1. Benchmark snapshot and class balance.
2. Label prediction and confusion matrices.
3. False fulfillment and abstention behavior.
4. Evidence retrieval.
5. Ablations and cost/runtime.
6. Error categories and qualitative cases.
7. Exploratory PURE observations.

### 8 Discussion and Threats to Validity

Discuss:

- why explicit evidence improves inspectability even without improving current label metrics;
- why retrieval and reasoning are separate bottlenecks;
- why claim decomposition can localize uncertainty but can also shift meaning;
- why screenshot verification has a principled visible/hidden boundary;
- why generated requirements and single-author annotation create circularity and consistency risks;
- why 13 web flows do not establish mobile or industrial generalization;
- why model versions, retries, cached outputs, and stale metrics affect reliability.

The strongest current empirical story is not that evidence-first is already more accurate. It is that the structured evaluation reveals where and why requirement verification fails.

### 9 Conclusion

Answer each research question directly. Summarize the problem formulation, prototype, benchmark, and observed failure patterns. Limit future work to concrete extensions: final annotation review, improved action/result retrieval, stronger uncertainty calibration, larger external datasets, and optional region grounding.

## 6. Evidence and Result Rules

Use only denominator-compatible results in the main tables. In particular:

- Do not use 169/259 or 173/258 as final performance.
- Do not use the stored 31.8% batched result; it scores 201 predictions against 258 gold items.
- Do not repeat the outdated 201-accepted/57-review statement.
- Do not combine the 100 Mind2Web candidates with 42 PURE candidates without labeling the sources.
- Do not present post-hoc PURE Mashboot labels as blinded gold.
- Do not interpret absent whole-flow evidence metrics as zero.

Every final table must include benchmark version, flows, item count, predictions, coverage, model, prompt version, claim policy, evidence strategy, aggregation, failures, and cost assumptions.

## 7. Remaining Work

### Before a Complete First Version

- Draft Background and Related Work.
- Draft Problem Definition and Approach from the implemented behavior.
- Convert the current Introduction and Evaluation draft into the final document template.
- Confirm the page target and AI-use disclosure with the supervisor.

### Before Final Results

- Freeze the 258-item benchmark and run manifest.
- Independently re-review a stratified annotation sample and adjudicate disagreements.
- Run every final configuration over flows 01–13.
- Normalize and compute whole-flow evidence metrics.
- Complete the requested ablations.
- Add confidence intervals and final cost/runtime/failure statistics.
- Freeze 3–5 qualitative cases.
- Decide the bounding-box scope.
- Document data licensing and artifact-release boundaries.

## 8. Current Main Argument

The thesis should conclude along the following line if the final results remain consistent with the current evidence:

> Ordered screenshot flows make visible UI requirement verification measurable, but they do not remove the uncertainty created by incomplete observation. Whole-flow multimodal models provide a strong label baseline, while explicit claim and evidence structures make decisions traceable and reveal retrieval failures. The main difficulties concentrate around partial evidence being over-generalized, decisive late states being missed, universal or comparative wording, and obligations whose truth is hidden from screenshots. Reliable verification therefore requires both stronger evidence selection and conservative reasoning about what the visible flow can actually establish.
