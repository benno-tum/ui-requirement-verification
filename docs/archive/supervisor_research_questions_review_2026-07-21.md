# Research-Question Lineage and Proposed Final Formulations

**Working title:** *Automated UI Requirement Verification from Ordered Screenshot Sequences*
**Student:** Benno Brueck
**Examiner:** Prof. Dr. Stefan Wagner
**Supervisor:** Mohamed Ben Salha
**Status:** Discussion draft for supervisor feedback, 21 July 2026

## Purpose of this memo

This memo makes the development of the research questions explicit. The registered proposal specifies three objectives but does not number formal research questions. The intermediate presentation subsequently introduced three method-oriented questions. The more recent thesis plan broadened these into outcome- and evaluation-oriented questions. This was an adaptation, not a verbatim continuation, and should be confirmed before the final thesis structure is frozen.

The requested feedback is:

1. Should claim decomposition remain a top-level research question, or be evaluated as a design factor under the comparative RQ2?
2. Is the proposed RQ2 sufficiently focused and supported by the planned controlled experiments?
3. Should the PURE question remain an explicitly exploratory fourth question?

## 1. Starting point: objectives in the registered proposal

The proposal defines three objectives rather than explicit RQs:

1. Design a verifier that maps an ordered screenshot sequence and textual requirements to one of four labels, together with explicit evidence.
2. Construct a small, high-quality evaluation basis from UI trajectories, complemented by a limited PURE comparison.
3. Test whether evidence discipline reduces false `FULFILLED` decisions relative to a naive multimodal verifier while preserving practical coverage through abstention.

The proposed evaluation also names label quality, evidence quality, false fulfillment, screenshot and region localization, and ablations for evidence enforcement, single versus multiple screenshots, ordering, and pipeline components.

## 2. Research questions used in the intermediate presentation

The June 2026 intermediate presentation used the following exact wording:

**Presentation RQ1:** Can textual UI requirements be decomposed into observable, hidden, and ambiguous claims?

**Presentation RQ2:** Can the system retrieve the screenshot steps that provide evidence for each claim?

**Presentation RQ3:** Can explicit uncertainty reduce unsafe fulfilled decisions?

These questions were deliberately simple and closely matched the pipeline modules. They were appropriate for explaining the system in a ten-minute presentation: requirement understanding, evidence retrieval, and uncertainty-aware decisions. They were not copied verbatim from the proposal and were not yet phrased as the final empirical questions of the thesis.

## 3. How the later four-question set differs

**Presentation RQ1 → later RQ1.** Decomposition into observable, hidden, and ambiguous claims was replaced by an umbrella question about overall verification accuracy. This lets the thesis answer whether the complete verifier works, not only whether one module produces plausible claims.

**Presentation RQ2 → part of later RQ2.** Retrieval of relevant screenshot steps became one experimental factor. It is measured through evidence hit@k/MRR and through its effects on labels, abstention, and cost.

**Presentation RQ3 → part of later RQ2.** The directional wording “reduce unsafe fulfilled decisions” was replaced by a neutral comparison. Current preliminary runs do not yet isolate or consistently demonstrate that benefit, although false fulfillment remains a primary outcome.

**New later RQ3.** Error analysis was promoted to a research question because the results show recurring, thesis-relevant patterns: hidden outcomes, universal claims, over-fulfillment, and missed late states.

**New exploratory RQ4.** The proposal’s limited PURE comparison was made explicit, while keeping it secondary because the present PURE annotations are not yet strong blinded gold evidence.

The main conceptual change is therefore not the invention of an unrelated RQ2. It is the merger of the presentation’s retrieval and uncertainty questions with the proposal’s third objective into one comparative evaluation question. Claim decomposition was moved from a top-level question to a design factor. That last choice is the point most in need of supervisor confirmation.

## 4. Recommended final research questions

I recommend three primary questions and one explicitly exploratory question:

**RQ1 — Overall verification performance**
How accurately can multimodal models verify textual UI requirements from ordered screenshot flows?

**RQ2 — Effect of the evidence-first design**
How do evidence selection, claim decomposition, and uncertainty-aware aggregation affect label quality, false fulfillment, abstention, evidence traceability, and cost compared with whole-flow verification?

**RQ3 — Failure conditions**
Which requirement and screenshot-flow characteristics cause the most frequent verification errors or abstentions, particularly over-fulfillment and missed decisive states?

**RQ4 — Exploratory transfer**
As an exploratory question, how well does the approach transfer to structured PURE requirements?

### Why this formulation is recommended

RQ1 provides the overall answer expected from a verification thesis. RQ2 preserves both earlier questions about retrieval and uncertainty but treats claimed improvements as hypotheses; its answer requires factor-controlled ablations rather than mixed historical runs. RQ3 captures the explanatory contribution supported by the current evidence. RQ4 preserves the proposal commitment without overstating the maturity or independence of the current PURE material.

## 5. Alternative if decomposition should remain a primary RQ

If the intended scientific emphasis is primarily requirements understanding rather than end-to-end system comparison, the following alternative retains the presentation’s first question:

**Alternative RQ1:** How reliably can textual UI requirements be decomposed into claims that distinguish observable, hidden, and ambiguous properties?

The overall performance question would then become part of the evaluation framing rather than a numbered RQ. This alternative requires a defensible decomposition evaluation: independent claim annotations, a documented matching protocol, and manual review of semantically equivalent decompositions. The current repository supports claim-level analysis, but independent decomposition validation is not yet complete. For that reason, the outcome-oriented RQ1 above is currently the safer main formulation.

## 6. Mapping from questions to evidence

**RQ1:** frozen benchmark, coverage, accuracy, macro-F1, per-class results, and confidence intervals. Preliminary full-coverage results exist; the final manifest and confidence intervals remain.

**RQ2:** controlled whole-flow/top-k, decomposition/no-decomposition, and aggregation comparisons, with false fulfillment, abstention, evidence metrics, cost, and runtime. Several configurations exist, but present rows differ in multiple factors; controlled reruns remain necessary.

**RQ3:** predefined error taxonomy, confusion analysis, and three to five frozen qualitative cases. Stable candidate patterns exist; final counts and examples remain to be frozen.

**RQ4:** a clearly separated PURE protocol with provenance and review limitations. Exploratory material exists, but it should not be presented as blinded external gold.

## 7. Decisions requested

Please advise on the following:

1. Approve the recommended set, or retain decomposition as a primary RQ.
2. Confirm whether RQ2 should cover all three factors—evidence selection, decomposition, and aggregation—or be narrowed to evidence selection and uncertainty only.
3. Confirm whether the proposed controlled ablations are sufficient to answer RQ2.
4. Confirm that PURE should remain an exploratory RQ rather than only a discussion subsection.

## Provenance checked for this memo

- Registered proposal: `proposal-requirement-verification.docx`, especially Objectives, Methods, and Evaluation.
- Intermediate presentation: `IntermediatePresentation.tex`, slide “Research questions,” June 2026.
- Intermediate-presentation content and speaker-notes plan, section “Research Questions In Plain Language.”
- Current thesis plan, implementation state, benchmark audit, and preliminary evaluation results as of 21 July 2026.
