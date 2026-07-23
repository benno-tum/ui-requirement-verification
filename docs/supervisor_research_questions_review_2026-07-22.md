# Proposed Final Research Questions - Supervisor Review

**Working title:** *Automated UI Requirement Verification from Ordered Screenshot Sequences*
**Student:** Benno Brueck
**Examiner:** Prof. Dr. Stefan Wagner
**Supervisor:** Mohamed Ben Salha
**Status:** Corrected discussion draft, 22 July 2026

## Purpose

This note reconciles the research questions shown in the intermediate presentation with the registered proposal, implemented pipeline, and current preliminary results. The presentation questions captured the intended contributions well, but two formulations are not yet sufficiently operational for the final thesis. The proposed revisions preserve their substance while defining comparisons and measurable outcomes.

## 1. Questions shown in the intermediate presentation

**RQ1:** Can ordered screenshot flows verify UI-observable requirements with evidence?

**RQ2:** Does claim decomposition make realistic long requirements easier to verify?

**RQ3:** Does abstention reduce unsafe fulfilled predictions under uncertainty?

These questions appear in the PowerPoint intermediate-presentation versions and accompanying speaker notes. A later LaTeX presentation expressed a related, more pipeline-oriented set. The three questions above are the appropriate lineage for the final thesis because they already cover the end-to-end task, claim decomposition, and abstention.

## 2. What the current evidence can and cannot establish

### RQ1: preliminary evidence exists, but the formulation is imprecise

The 258-item preliminary benchmark shows that multimodal models can produce requirement labels and screenshot-step evidence. The strongest current full-coverage run reaches 78.3% accuracy, 0.560 macro-F1, 7.6% false fulfillment, and evidence MRR 0.899. This supports feasibility, not production readiness.

The wording should identify the verifier as the actor: screenshot flows are evidence inputs and do not themselves perform verification. “With evidence” should also be evaluated separately through traceability metrics rather than treated as a yes/no property.

### RQ2: no causal conclusion yet

The current runs do not prove that claim decomposition improves verification. Provided-claim and raw-requirement runs differ simultaneously in model, screenshot selection, prompts, grouping, and grounding. The provided-claim runs also use benchmark claims by construction and therefore do not evaluate automatic decomposition quality.

“Easier to verify” is undefined. The final question should instead name observable outcomes such as macro-F1, false fulfillment, evidence recall, and cost. “Realistic long requirements” should be replaced by the more precise “compound or multi-obligation requirements.”

### RQ3: no clean causal conclusion yet

The current mixed runs do not establish that abstention alone reduces unsafe fulfilled predictions. Their abstention rates are 6.2%, 7.4%, and 27.1%, while false-fulfillment rates are 7.6%, 12.4%, and 10.5%, respectively. Because an always-abstain system could eliminate fulfilled errors trivially, the relevant outcome is the trade-off between coverage and false fulfillment under a fixed model and evidence setting.

## 3. Recommended final set

I recommend retaining three primary research questions, with the following measurable wording.

### RQ1 - End-to-end performance and traceability

**How accurately, and with what evidence traceability, can multimodal models verify UI-observable textual requirements from ordered screenshot flows?**

Primary evidence: accuracy, macro-F1, per-class precision and recall, false fulfillment, prediction coverage, evidence hit@k, evidence recall@k, and MRR on the frozen benchmark.

### RQ2 - Claim decomposition and evidence selection

**How do claim decomposition and screenshot selection affect verification performance, evidence traceability, and cost for compound UI requirements relative to direct whole-flow verification of the original requirement text?**

Primary evidence: factor-controlled comparisons of decomposed versus undecomposed requirements and all-screenshot versus top-k input, while holding model, prompt family, aggregation, and benchmark constant.

### RQ3 - Abstention and safety

**How does explicit abstention affect the trade-off between prediction coverage and false fulfillment when screenshot evidence is insufficient or a requirement contains non-observable claims?**

Primary evidence: a fixed-verifier comparison of aggregation/abstention policies, risk-coverage analysis, abstention reasons, and separate results for UI-verifiable, partially UI-verifiable, and non-UI-verifiable requirements.

## 4. PURE as exploratory analysis, not a core RQ

The proposal commits to a limited PURE comparison, but the current PURE artifacts do not provide equivalent executed screenshot flows or independently blinded gold labels. A transfer-performance RQ would therefore overstate the evidence.

The defensible exploratory question is:

**How do structured PURE requirements differ from trajectory-derived requirements in compoundness, context dependence, and UI verifiability?**

This can be reported as an exploratory subsection or appendix rather than as RQ4. If the supervisor prefers four numbered questions, it should be explicitly labelled exploratory.

## 5. Why this set is preferable

- It preserves the substantive intent of all three presentation questions.
- Each RQ identifies measurable outcomes and an appropriate comparison.
- It does not assume that decomposition or abstention improves the result.
- It separates end-to-end feasibility, pipeline design choices, and the safety-coverage trade-off.
- It matches the proposal while respecting the current limitations of PURE and screenshot-only evidence.

```{=typst}
#pagebreak()
```

## 6. Experiments required before final answers

1. Freeze the 258-item benchmark and run manifest.
2. Run a controlled 2x2 comparison: decomposed versus original requirements, crossed with all screenshots versus top-k screenshots, using the same model and aggregation.
3. Compare fixed claim outputs under alternative aggregation/abstention policies and report risk-coverage curves or threshold tables.
4. Add confidence intervals and flow-cluster-aware interpretation.
5. Freeze an error taxonomy and three to five qualitative cases, including insufficient evidence, hidden claims, and missed late states.

## 7. Decisions requested from the supervisor

1. Approve the three revised core questions or indicate which should be narrowed.
2. Confirm whether RQ2 should include both claim decomposition and screenshot selection, or only decomposition.
3. Confirm whether PURE should remain an exploratory subsection rather than a numbered RQ.
4. Confirm that a controlled 2x2 ablation and a risk-coverage analysis are sufficient to answer RQ2 and RQ3 within the bachelor-thesis scope.

## Sources checked

- Registered proposal, especially Objectives, Methods, and Evaluation.
- PowerPoint intermediate-presentation drafts and speaker notes, slide 2.
- Later native LaTeX intermediate-presentation deck.
- Current 258-item evidence audit and full-coverage preliminary results.
- Current thesis plan and research-question-to-evidence map.
