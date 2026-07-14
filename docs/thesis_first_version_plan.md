# First Thesis Version Plan

Working title: **Automated UI Requirement Verification from Ordered Screenshot Sequences**

This document is a writing scaffold for the first thesis draft. It is based on the proposal, repository docs, current annotation data, generated verification results, the intermediate presentation plan, and a small literature check.

## Current Thesis Claim

The thesis should argue that verifying textual UI requirements against screenshot flows is not just a label prediction problem. It is a traceability and uncertainty problem: a useful verifier must connect each decision to visible evidence in an ordered flow and must abstain or downgrade the decision when screenshots do not prove the requirement.

The most defensible contribution is therefore:

1. a problem formulation for evidence-grounded UI requirement verification over ordered screenshot flows;
2. an evidence-first pipeline with requirement decomposition, screenshot evidence retrieval, claim verification, and conservative aggregation;
3. a manually reviewed benchmark subset over Mind2Web flows with requirement-level, claim-level, and evidence-step annotations;
4. an empirical analysis showing that the task is hard in specific, interpretable ways: over-fulfillment, missing late-state evidence, universal/comparative claims, result-state claims, and hidden/system-outcome claims.

Bounding boxes and PURE should be treated carefully. The proposal mentions spatial evidence and PURE comparison. The current repository mainly supports step-level evidence; bounding boxes are schema/future-work rather than a mature evaluated result. PURE extraction is technically prepared and test-covered, but the current main evaluation basis is Mind2Web.

## Template And Formal Structure

I did not find a local LaTeX thesis template in the repository. The proposal document gives the chair-facing structure and constraints: examiner Prof. Dr. Stefan Wagner, supervisor Mohamed Ben Salha, timeframe 2026-04-02 to 2026-08-03, and a proposal organized as Context & Motivation, Objectives, Methods, Evaluation, References.

For the written thesis, use the standard empirical software engineering structure:

1. Introduction
2. Background and Related Work
3. Problem Definition
4. Approach
5. Dataset and Annotation Methodology
6. Evaluation Design
7. Results
8. Discussion
9. Threats to Validity
10. Conclusion

This maps cleanly to the proposal and to the current codebase. If the chair template later enforces different names, this structure can be adapted without changing the argument.

## Chapter Plan

### 1. Introduction

Goal: motivate the problem and state the contributions without over-claiming.

Paragraph plan:

1. UI requirements are often written in natural language, while the UI evidence is visual and state-based. This creates a mismatch between textual requirements and screenshot artifacts.
2. Manual UI checking is expensive and can be inconsistent, especially when requirements depend on navigation, validation, persistence proxies, or multi-step flows.
3. Existing GUI automation and UI-agent work shows the importance and difficulty of visual UI understanding, but a verifier has a special risk: it can falsely mark a requirement as fulfilled without sufficient evidence.
4. Define the thesis setting: input is an ordered screenshot flow and textual requirements; output is a verdict in `FULFILLED`, `PARTIALLY_FULFILLED`, `NOT_FULFILLED`, or `ABSTAIN`, together with evidence steps and claim-level explanations.
5. State the central principle: no `FULFILLED` without visible support for all central observable claims; missing evidence alone is not `NOT_FULFILLED`.
6. Contributions: pipeline, annotation schema/benchmark, evaluation metrics, error analysis.

Important citations:

- Requirements ambiguity: Berry/Kamsties/Krieger; Gervasi/Ferrari/Zowghi/Spoletini.
- Traceability: Cleland-Huang et al. FOSE 2014.
- GUI automation difficulty: Nass et al. 2021.
- Multimodal verification: Massenon et al. 2025.
- Abstention/reject option: Hendrickx et al. 2021 or Wen et al. 2024.

### 2. Background And Related Work

Goal: explain why this task sits between requirements engineering, GUI testing/automation, visual grounding, and uncertainty-aware verification.

Suggested subsections:

#### 2.1 Requirements Ambiguity And Traceability

Argument:

- Natural-language requirements can be vague, compound, context-dependent, or quantified.
- Verification needs a trace link between requirement statements and artifacts.
- In this thesis, the trace link is not requirement-to-code but requirement-to-screenshot-step and claim-to-evidence.

Use this to justify claim decomposition and evidence annotations.

#### 2.2 GUI Testing And UI Automation

Argument:

- GUI testing is hard because UI behavior is stateful and sequence-dependent.
- Screenshot flows are weaker than executable tests: they show what happened, not all possible behavior.
- Therefore the thesis verifies visible UI contracts, not backend correctness.

Use Nass et al. and optionally GUI testing literature for sequence/state-space problems.

#### 2.3 Multimodal UI Understanding And Grounding

Argument:

- Recent datasets and models such as Mind2Web, Android in the Wild, and SeeClick show that language-conditioned UI understanding and grounding are active research areas.
- This thesis reuses the ordered flow idea from agent datasets but changes the task: instead of choosing the next action, it verifies whether a textual requirement is visibly satisfied.
- Grounding motivates future bounding boxes, but current evaluation focuses primarily on screenshot-step evidence.

#### 2.4 Abstention And Evidence Discipline

Argument:

- A model that always predicts a concrete label is unsafe for incomplete evidence.
- Reject-option or abstention literature supports refusing decisions when uncertainty is high.
- The thesis adapts this idea to UI verification: `ABSTAIN` is not a failure mode but a necessary output when screenshots cannot decide.

### 3. Problem Definition

Goal: make the task precise before describing implementation.

Define:

- Screenshot flow: ordered sequence of UI screenshots, optionally with HTML/OCR/summary sidecars.
- Requirement: textual UI-facing requirement.
- Claim: atomic semantic obligation decomposed from the requirement text.
- Evidence unit: step index, screenshot path, visible observation, and later possibly bounding box.
- UI evaluability: `UI_VERIFIABLE`, `PARTIALLY_UI_VERIFIABLE`, `NOT_UI_VERIFIABLE`.
- Verification labels: `FULFILLED`, `PARTIALLY_FULFILLED`, `NOT_FULFILLED`, `ABSTAIN`.
- Claim statuses: `SUPPORTED`, `CONTRADICTED`, `MISSING`, `HIDDEN`, `AMBIGUOUS`, `OUT_OF_SCOPE`.

Paragraph plan:

1. Formalize input and output.
2. Explain why UI evaluability is separate from final fulfillment.
3. Explain the conservative label policy.
4. Give one running example, preferably the Amtrak onboard dining requirement from the presentation plan.
5. Show how a stronger hidden requirement changes the label from `FULFILLED` to `PARTIALLY_FULFILLED` or `ABSTAIN`.

Recommended running example:

Requirement: "The system shall make onboard dining information and cafe menu resources discoverable through public site navigation without requiring the user to sign in."

Claims:

- Onboard dining information and cafe menu resources are discoverable through public navigation.
- The user is not required to sign in.

This is useful because it is easy to explain, visible across multiple screens, and not purely single-screen.

### 4. Approach

Goal: describe the implemented pipeline at a level suitable for a thesis, not as a code walkthrough.

Suggested subsections:

#### 4.1 Evidence-First Pipeline Overview

Use the existing pipeline:

1. screen understanding;
2. requirement understanding;
3. evidence retrieval;
4. claim verification;
5. label aggregation.

Argument:

- The verdict comes after evidence selection, not before.
- Intermediate outputs make errors inspectable.
- Expensive vision reasoning is applied only after selecting candidate evidence.

#### 4.2 Requirement Understanding And Claim Decomposition

Describe:

- deterministic rule-based decomposition as baseline/fallback;
- optional rule-guided LLM decomposition;
- claims are prediction artifacts, not gold evidence;
- gold claims are only used for evaluation.

Key writing point:

The thesis should emphasize that claims are derived from requirement text only. Evidence-specific details belong in evidence notes, not claim text.

#### 4.3 Evidence Retrieval

Describe:

- lexical retrieval as deterministic baseline;
- optional TF-IDF, embedding, and text-only LLM reranking support;
- retrieval returns top-k candidate screenshot steps per claim.

Current result to motivate:

Evidence retrieval is a major bottleneck, especially for late cart, checkout, result, review, and summary screens. This should become a clear thesis finding.

#### 4.4 Screenshot-Grounded Claim Verification

Describe:

- rule-based placeholder verifier for deterministic baseline;
- Gemini image verifier for screenshot-grounded claim status decisions;
- verifier receives claim and selected screenshots, then predicts claim status and rationale.

Careful wording:

Do not claim the verifier proves backend truth. It judges visible UI evidence.

#### 4.5 Conservative Aggregation

Describe:

- `FULFILLED` requires all central observable claims supported and at least one evidence item.
- `PARTIALLY_FULFILLED` captures mixed visible support and unresolved/missing/hidden claims.
- `NOT_FULFILLED` requires visible contradiction.
- `ABSTAIN` captures insufficient evidence or non-visible requirements.

This is one of the most important sections because it contains the main methodological idea.

### 5. Dataset And Annotation Methodology

Goal: make the benchmark construction defensible.

Current repository facts:

- `requirements_candidate`: 13 files, 100 candidate requirements.
- `requirements_gold`: 13 files, 173 accepted requirement texts.
- `verification_gold`: 13 files, 258 verification items.
- Current verification-gold review status: 201 accepted, 57 needs review.
- Current verification-gold label distribution: 171 `FULFILLED`, 45 `PARTIALLY_FULFILLED`, 33 `ABSTAIN`, 9 `NOT_FULFILLED`.

Suggested subsections:

#### 5.1 Source Flows

Main dataset: 13 Mind2Web flows in the repository dataset.

Explain why Mind2Web is appropriate:

- real-world websites;
- ordered user trajectories;
- natural multi-step UI states;
- diverse websites/tasks.

#### 5.2 Requirement Generation And Review

Explain the staged process:

1. harvested broad hypotheses;
2. candidate requirements;
3. human-reviewed gold requirements;
4. verification-gold items with labels, claims, evidence, rationale, uncertainty reasons.

Important anti-circularity argument:

Generated requirements are not automatically gold. Human review is needed to avoid a self-fulfilling evaluation where the same model assumptions create both requirements and predicted labels.

#### 5.3 Contrastive Requirements

Explain:

- contrastive requirements are deliberately modified versions of positive requirements;
- they create harder partial, negative, or abstention cases;
- automatically generated intended labels are not gold until reviewed.

Use this to explain why the benchmark contains more than trivial visible-positive cases.

#### 5.4 PURE As Secondary External Material

Current status:

- PURE extraction is implemented and tested.
- It preserves document context, sections, local labels, and context-required flags.
- It is suitable for claim-decomposition stress testing and comparison, but not yet the main verification benchmark.

Thesis framing:

Use PURE to discuss external requirement realism and longer/context-dependent requirements. Avoid presenting it as a full verification evaluation unless additional results are produced.

### 6. Evaluation Design

Goal: connect metrics to research questions.

Recommended research questions:

RQ1: Can textual UI requirements be decomposed into checkable claims that separate visible, hidden, missing, and ambiguous obligations?

RQ2: Can the pipeline retrieve the screenshot steps needed to support or reject the claims?

RQ3: Does an evidence-first, uncertainty-aware verifier reduce unsafe `FULFILLED` predictions compared with simpler baselines?

RQ4: Which requirement patterns cause the most frequent failures?

Metrics:

- Label quality: accuracy, macro-F1, weighted-F1, per-class precision/recall/F1, confusion matrix.
- Safety: false fulfillment rate.
- Coverage/uncertainty: abstain rate, prediction coverage.
- Evidence quality: precision@k, recall@k, hit@k, MRR over evidence steps.
- Claim quality: claim-status macro-F1, claim match recall.

Baselines and ablations to include:

- deterministic/rule-based baseline;
- image-grounded Gemini verifier;
- no claim decomposition;
- all screenshots vs top-k retrieval;
- ordered vs shuffled screenshots if time permits;
- Flow 10 late-state retrieval ablation as qualitative/targeted evidence.

### 7. Results

Goal: report current findings honestly, separating final numbers from preliminary ones.

Current numeric material:

1. Older/current cross-flow note: 169/259 = 65.3% in `docs/accuracy_analysis_2026-06-25.md`.
2. Systematic error analysis: 173/258 = 67.1% and over-fulfillment as dominant bias in `docs/systematic_error_analysis_and_review_plan_2026-07-02.md`.
3. Diagnosis run with Gemini Flash Lite:
   - accuracy 0.486
   - macro-F1 0.276
   - false fulfillment rate 0.106
   - evidence hit@1 0.344
   - evidence hit@3 0.436
4. Deterministic strict aggregation baseline:
   - accuracy 0.266
   - macro-F1 0.168
   - false fulfillment rate 0.196
   - evidence hit@1 0.201
   - evidence hit@3 0.429
5. July 9 batched top-k gated real-API run over 01-10 appears worse/less complete:
   - accuracy 0.318
   - macro-F1 0.182
   - false fulfillment rate 0.329
   - prediction coverage 0.779
   - evidence hit@1 0.205
   - evidence hit@3 0.248

Writing strategy:

- Treat these as preliminary until the benchmark split and run configuration are frozen.
- Do not mix incompatible runs as one final table.
- Use them to support the qualitative finding that evidence-first design exposes bottlenecks.
- The clearest positive comparison is diagnosis Gemini vs deterministic strict baseline, but verify the exact run setup before final thesis claims.

Suggested results subsections:

#### 7.1 Dataset Snapshot

Report reviewed item counts and label distribution.

#### 7.2 Label Prediction

Show accuracy/macro-F1/confusion matrix for the frozen runs.

Key interpretation:

Macro-F1 matters because labels are imbalanced. Accuracy alone is misleading because `FULFILLED` dominates.

#### 7.3 False Fulfillment

This should be a central result.

Argument:

Unsafe false `FULFILLED` predictions are especially harmful because they claim requirement satisfaction without sufficient evidence. The thesis should therefore discuss false fulfillment separately from general accuracy.

#### 7.4 Evidence Retrieval

Show hit@1/hit@3/MRR and qualitative examples.

Main finding:

Retrieval often finds partial evidence, but misses decisive late states for cart, checkout, result, review, and summary requirements.

#### 7.5 Error Categories

Use the systematic categories:

- over-fulfillment bias;
- anti-abstain bias;
- under-calling/over-abstaining due to missed evidence;
- boundary errors.

Dominant semantic patterns:

- universal/comparative claims;
- late-state cart/checkout claims;
- result/search-output claims;
- persistence/cross-step claims;
- hidden/external behavior;
- review/summary-state claims.

### 8. Discussion

Goal: explain what the results mean beyond the numbers.

Paragraph plan:

1. The task is not solved by stronger prompting alone; failures split into label policy, retrieval, and reasoning limitations.
2. Evidence discipline is valuable even when accuracy is moderate because it reveals why a verdict was reached.
3. Claim decomposition helps localize uncertainty but introduces its own evaluation problem: predicted claims must be matched to gold claims.
4. Top-k retrieval creates a tradeoff: too many screenshots dilute model attention and cost; too few miss necessary evidence.
5. Screenshot-only verification has a principled boundary: it can verify visible UI contracts and success proxies, but not hidden backend truth.
6. Human review remains essential because generated requirements can otherwise create circularity and label ambiguity.

### 9. Threats To Validity

Suggested structure:

#### Internal Validity

- manual labels still partly `needs_review`;
- possible label inconsistency in boundary cases;
- generated requirements may encode model assumptions;
- different runs/configurations are not always directly comparable.

#### Construct Validity

- step-level evidence is weaker than bounding-box evidence;
- `FULFILLED`/`PARTIALLY_FULFILLED` boundaries depend on label policy;
- screenshots do not observe hidden system state.

#### External Validity

- 13 Mind2Web flows are small;
- web flows may not generalize to mobile/native UI;
- PURE extraction covers only selected XML shapes;
- real industrial requirements may be longer and more context-dependent.

#### Reliability

- LLM/API runs can fail or produce malformed outputs;
- Flow 01 had Gemini 503 fallbacks in older runs;
- exact model versions and prompts must be recorded.

### 10. Conclusion

Goal: close with a measured statement.

Paragraph plan:

1. Restate the problem: checking textual UI requirements against ordered screenshots requires evidence and uncertainty, not only labels.
2. Summarize the approach: claim decomposition, evidence retrieval, screenshot-grounded verification, conservative aggregation.
3. Summarize empirical finding: current benchmark exposes over-fulfillment, missed late-state evidence, and hidden/system-outcome limits.
4. State future work: finish review, freeze benchmark, improve retrieval, add bounding-box localization, expand PURE/external evaluation.

## First Draft Writing Order

The fastest path to a readable first version is not chapter order.

1. Write Chapter 3 first: problem definition and label schema.
2. Write Chapter 4: approach.
3. Write Chapter 5: dataset and annotation methodology.
4. Write Chapter 6: evaluation metrics.
5. Draft Chapter 7 with preliminary numbers and mark tables as provisional.
6. Write Introduction after the core is stable.
7. Write Related Work after the argument is fixed, because citations should support the thesis rather than dictate it.
8. Write Discussion and Threats last.

## Research And Citation Checklist

Already in proposal or current docs:

- Kretzer et al. / Kolthoff et al. on user stories and GUI prototypes.
- Cleland-Huang et al. on traceability.
- Nass, Alégroth, Feldt on persistent GUI test automation challenges.
- Massenon et al. on multimodal app bug-fix verification.
- Rawles et al. on Android in the Wild.
- Deng et al. on Mind2Web.
- Cheng et al. on SeeClick and GUI grounding.
- Ferrari et al. on PURE.

Additional citations to add or verify:

- Berry, Kamsties, Krieger: requirements ambiguity taxonomy.
- Gervasi, Ferrari, Zowghi, Spoletini: ambiguity as recurring RE problem.
- Hendrickx et al. 2021: machine learning with reject option.
- Wen et al. 2024 or Tomani et al. 2024: LLM abstention/hallucination framing.
- Optional GUI testing classic: Memon et al. for GUI event sequence/state-space difficulty.

Useful source links from the research check:

- Mind2Web: https://arxiv.org/abs/2306.06070
- Android in the Wild: https://arxiv.org/abs/2307.10088
- SeeClick: https://arxiv.org/abs/2401.10935
- Machine Learning with a Reject Option: https://arxiv.org/abs/2107.11277
- Know Your Limits: A Survey of Abstention in Large Language Models: https://arxiv.org/abs/2407.18418
- Interlinking User Stories and GUI Prototyping: https://arxiv.org/abs/2406.08120

## Data Needed Before Final Writing

Must-have:

- freeze the reviewed verification-gold subset;
- decide whether to evaluate all 258 items or accepted-only;
- rerun final pipeline configurations consistently;
- generate one final metrics JSON per configuration;
- save run metadata: model, prompt versions, top-k, claim decomposition strategy, date, fallback counts;
- produce confusion matrix and evidence metrics tables;
- select 3-5 representative qualitative cases.

Should-have:

- accepted-only vs all-items metrics;
- error-category counts after final review;
- Flow 10 late-state retrieval ablation;
- claim-status metrics with claim match recall;
- cost/runtime summary if API usage logs are reliable.

Nice-to-have:

- PURE claim decomposition inspection table;
- bounding-box demonstration for one or two examples, clearly marked as prototype/future work if not evaluated;
- shuffled-order or all-screenshot ablation.

## Recommended Main Argument

The thesis should not argue "the model achieves high accuracy." The current numbers are too preliminary and the task is too small for that to be the main story.

The stronger argument is:

> Ordered screenshot flows make UI requirement verification measurable, but also expose why naive multimodal verification is unsafe. By decomposing requirements into claims, retrieving explicit evidence, and allowing abstention, the verifier can separate visible support from missing, hidden, or ambiguous parts of a requirement. The resulting benchmark and error analysis show that the main challenges are not random: they concentrate around over-fulfillment, late-state evidence retrieval, universal/comparative wording, result correctness, and hidden system outcomes.

This argument fits the proposal, the implementation, and the current results.
