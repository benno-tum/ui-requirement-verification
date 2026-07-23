# Thesis Structure and Scope - Supervisor Review

**Working title:** Automated UI Requirement Verification from Ordered Screenshot Sequences
**Examiner:** Prof. Dr. Stefan Wagner
**Supervisor:** Mohamed Ben Salha
**Registered timeframe:** 2 April 2026 to 3 August 2026
**Document status:** Discussion draft for supervisor feedback, 21 July 2026

## 1. Purpose of This Review

This document proposes the final thesis structure and identifies the remaining decisions needed before the complete first version is assembled. It reconciles the registered proposal with the implemented system, current annotations, and preliminary evaluation results.

The requested feedback concerns five points:

1. Is the proposed eight-chapter structure appropriate?
2. Are the three research questions sufficiently focused?
3. Should bounding-box localization remain an evaluated contribution or be presented as exploratory implementation work?
4. Is the proposed treatment of PURE as an exploratory comparison appropriate?
5. Is a target of approximately 42 pages of core text suitable for this thesis?

## 2. Thesis Position in One Paragraph

The thesis studies whether multimodal models can verify textual UI requirements from ordered screenshot flows while providing explicit evidence and preserving uncertainty. The central position is that this is not only a classification problem. A useful verifier must connect each decision to visible states, distinguish partial observation from contradiction, and abstain when screenshots cannot establish the requested property. The work therefore evaluates both requirement-label quality and evidence traceability, with particular attention to unsafe `FULFILLED` predictions. Hidden backend correctness, security, persistence, external effects, and global completeness remain outside the claims that screenshots can support.

## 3. Motivation and Research Gap

Coding-agent capabilities have advanced rapidly, but measured end-to-end productivity effects remain dependent on task and development context (Kwa et al., 2025; Jimenez et al., 2024; Becker et al., 2025). The motivation is therefore not that software implementation has universally become fast. Rather, as candidate implementations become cheaper to produce, expressing intent precisely and verifying generated behaviour become relatively more important.

UI requirements are a useful setting because their implementation evidence is visual, stateful, and distributed across interaction steps. Existing work studies requirements-to-GUI prototype support (Kretzer et al., 2025), requirements traceability (Cleland-Huang et al., 2014), GUI test automation (Nass, Alegroth, and Feldt, 2021), UI-agent trajectories (Deng et al., 2023), GUI grounding (Cheng et al., 2024), and cross-modal bug-fix verification (Massenon, Gambo, and Khan, 2026). The remaining gap is conservative requirement verification over already recorded ordered UI states with explicit evidence, partial labels, and abstention.

## 4. Proposed Research Questions

**RQ1:** How accurately can multimodal models apply a provided, application-specific verification label schema to UI-observable textual requirements using ordered screenshot flows?

**RQ2:** How do claim decomposition and screenshot selection affect label accuracy, evidence traceability, and cost relative to direct whole-flow verification?

**RQ3:** Which requirement and evidence patterns cause verification errors, abstentions, or unsafe `FULFILLED` predictions?

RQ2 is deliberately neutral and isolates claim decomposition and screenshot selection. RQ3 analyzes observed abstentions and unsafe positive predictions without presupposing a causal safety benefit. PURE remains exploratory rather than a numbered RQ.

**Decision requested:** approve these formulations or identify any RQ that should be narrowed, combined, or removed.

## 5. Proposed Table of Contents and Page Budget

| Chapter | Pages | Main content |
|---|---:|---|
| 1. Introduction | 4 | Motivation, problem, gap, RQs, contributions, scope. |
| 2. Foundations and Related Work | 6 | Requirements, traceability, GUI verification, UI agents, grounding, abstention. |
| 3. Research Design and Problem Formulation | 4 | Formal task, labels, evaluability, claims, evidence, visible/hidden boundary. |
| 4. Verification Approach and Implementation | 7 | Ordered screens, claim policy, evidence selection, multimodal verification, aggregation, workbench. |
| 5. Benchmark Construction and Annotation | 5 | Mind2Web-derived benchmark, contrastive items, review, statistics, PURE. |
| 6. Evaluation | 10 | Configurations, metrics, results, evidence, ablations, efficiency, errors. |
| 7. Discussion | 4 | RQ answers, implications, validity threats, limitations. |
| 8. Conclusion | 2 | Contributions, concise answers, future work. |
| **Total core text** | **42** | Excludes front matter, bibliography, and appendices. |

The structure follows the successful chair pattern of separating foundations, research design, implementation, evaluation, discussion, and conclusion. Benchmark construction remains a separate chapter because the reviewed labels, claims, evidence, and contrastive requirements are a substantive contribution.

### Proposed Subsection Structure

**1. Introduction**

1.1 Motivation
1.2 Problem Statement and Research Gap
1.3 Objective and Research Questions
1.4 Contributions
1.5 Scope and Thesis Organization

**2. Foundations and Related Work**

2.1 Requirements Quality, Ambiguity, and Traceability
2.2 GUI Verification and Ordered Interaction State
2.3 Multimodal UI Agents and Interaction Datasets
2.4 Requirement-to-UI and Cross-Modal Verification
2.5 Visual Grounding and Evidence Localization
2.6 Abstention and Selective Prediction
2.7 Gap Synthesis

**3. Research Design and Problem Formulation**

3.1 Research Design
3.2 Formal Verification Task
3.3 UI Evaluability and Requirement Labels
3.4 Claim Statuses, Evidence, and Aggregation
3.5 Epistemic Boundary

**4. Verification Approach and Implementation**

4.1 Architecture Overview
4.2 Ordered Screen Representation
4.3 Requirement Understanding and Claim Policy
4.4 Evidence Selection
4.5 Multimodal Claim Verification
4.6 Requirement Aggregation and Safety Gates
4.7 Candidate-Mark Grounding
4.8 Annotation Workbench and Reproducibility

**5. Benchmark Construction and Annotation**

5.1 Data Source and Flow Selection
5.2 Requirement Construction Funnel
5.3 Annotation Schema and Review Protocol
5.4 Benchmark Statistics and Temporal Properties
5.5 Contrastive Requirements
5.6 Exploratory PURE Material
5.7 Quality and Release Boundaries

**6. Evaluation**

6.1 Evaluation Questions and Frozen Manifest
6.2 Compared Configurations
6.3 Metrics and Statistical Analysis
6.4 Requirement-Label Results
6.5 Evidence Traceability Results
6.6 Controlled Ablations
6.7 UI-Evaluability and Grounding Analyses
6.8 Efficiency and Reliability
6.9 Error Analysis and Qualitative Cases

**7. Discussion**

7.1 Answers to the Research Questions
7.2 What Evidence-First Verification Does and Does Not Provide
7.3 Implications for Requirements Engineering and Verification
7.4 Threats to Validity
7.5 Limitations and Future Work

**8. Conclusion**

8.1 Summary of Contributions
8.2 Final Answers
8.3 Outlook

**Decision requested:** confirm the chapter separation, especially whether Research Design and Problem Formulation should remain one chapter and whether Benchmark Construction warrants its own chapter.

## 6. Proposal Alignment and Necessary Adaptations

The proposal's main problem and architecture remain intact:

- textual requirements are verified against ordered screenshots;
- the output uses four requirement labels and explicit evidence;
- the system separates requirement understanding, evidence selection, multimodal verification, and aggregation;
- the main benchmark is trajectory-based and PURE provides a limited structured-requirement comparison;
- false fulfillment is a primary safety-oriented metric;
- hidden backend, security, and performance truth is excluded.

Three adaptations are necessary based on the implemented work and available evidence:

1. **Evidence benefit is a hypothesis.** Current results do not support assuming that an evidence-first configuration will outperform whole-flow prompting. Traceability and classification performance must be evaluated separately.
2. **PURE is exploratory.** PURE figures generally describe intended designs rather than observations from an executed flow. PURE is most defensible for studying extraction, contextualization, compound requirements, and document-to-UI consistency.
3. **Bounding boxes are conditional.** Screenshot-step evidence is mature. Candidate-mark grounding is implemented over all 13 flows, but the generated regions are not yet independently evaluated for relevance and sufficiency.

## 7. Current Empirical Basis

### Main Benchmark

The current Mind2Web-derived benchmark contains:

- 13 ordered web flows;
- 173 reviewed source requirements;
- 85 reviewed contrastive items;
- 258 accepted verification items;
- 541 claims;
- 172 `FULFILLED`, 45 `PARTIALLY_FULFILLED`, 33 `ABSTAIN`, and 8 `NOT_FULFILLED` labels.

All Mind2Web items received primary-author review. Acceptance does not represent independent annotator agreement.

### Current Full-Coverage Preliminary Results

| Configuration | Accuracy | Macro-F1 | False fulfillment | Abstain | Evidence MRR |
|---|---:|---:|---:|---:|---:|
| Gemini 3.1 Pro, all screenshots, provided claims | 78.3% | 0.560 | 7.6% | 6.2% | 0.899 |
| Gemini 3.1 Flash-Lite, all screenshots, provided claims, joint grounding | 76.7% | 0.528 | 12.4% | 7.4% | 0.808 |
| Gemini 3.1 Flash-Lite, lexical top-4, raw requirements, no decomposition | 72.1% | 0.449 | 10.5% | 27.1% | 0.606 |

Every row covers 258/258 items. These results are denominator-compatible but not a clean causal comparison: the configurations differ in model strength, claim policy, screenshot selection, grouping, and grounding.

The strongest current interpretation is therefore:

- multimodal verification is feasible but minority labels remain difficult;
- explicit evidence makes traceability measurable;
- the current results do not isolate whether evidence-first processing improves label safety;
- raw-requirement top-k processing abstains considerably more often and retrieves less of the reference evidence;
- decisive late states, partial visible evidence, hidden outcomes, and universal wording remain important error sources.

### Exploratory PURE Status

Split/Merge currently contains 31 accepted items with 78 claims. Mashboot contains 11 accepted items. Most Mashboot provenance and some Split/Merge provenance remain Codex-draft, and Mashboot annotation began after predictions were inspected. These items should therefore not be presented as blinded external gold.

### Region Grounding Status

The July 21 joint candidate-grounding run produced 541 claim decisions and 588 stored evidence regions. This establishes implementation coverage, not localization accuracy. A prediction-independent review of region relevance and sufficiency is required before region grounding can be a validated contribution.

## 8. Remaining Work Before Final Claims

The following work is still required:

1. Freeze the 258-item benchmark and complete run manifest.
2. Independently re-review a stratified annotation sample and adjudicate disagreements.
3. Run factor-controlled all-screenshots versus top-k, claim-policy, ordered-versus-shuffled, and aggregation comparisons.
4. Add confidence intervals and final runtime, failure, image, token, and cost statistics.
5. Freeze three to five qualitative examples and an explicit error-category protocol.
6. Document Mind2Web and PURE licensing and artifact-release boundaries.
7. Either evaluate the generated regions independently or move bounding-box results to an exploratory subsection or appendix.

The implementation currently passes 203 automated tests. This supports repository consistency but is not evidence of scientific validity.

## 9. Decisions Requested from the Supervisor

Please provide guidance on the following points:

- **Structure:** approve the eight-chapter organization and approximately 42-page target.
- **Research questions:** approve the three final formulations and keep PURE exploratory rather than as a numbered RQ.
- **Bounding boxes:** retain as an evaluated contribution, or present as exploratory work unless human review is completed.
- **PURE:** keep the current exploratory document-to-UI analysis, move it to an appendix, or remove quantitative PURE results.
- **Annotation review:** confirm whether a stratified second-review sample is sufficient and, if so, the expected sample size.
- **AI-use disclosure:** confirm permitted use of AI-assisted planning and language drafting and the required declaration format.

## 10. Core References

Becker, J. et al. (2025). *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*. arXiv:2507.09089.

Cheng, K. et al. (2024). *SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents*. ACL 2024. DOI: 10.18653/v1/2024.acl-long.505.

Cleland-Huang, J. et al. (2014). *Software Traceability: Trends and Future Directions*. FOSE 2014. DOI: 10.1145/2593882.2593891.

Deng, X. et al. (2023). *Mind2Web: Towards a Generalist Agent for the Web*. NeurIPS 2023.

Ferrari, A., Spagnolo, G. O., and Gnesi, S. (2017). *PURE: A Dataset of Public Requirements Documents*. IEEE RE 2017. DOI: 10.1109/RE.2017.29.

Hendrickx, K. et al. (2024). *Machine Learning with a Reject Option: A Survey*. Machine Learning 113, 3073-3110. DOI: 10.1007/s10994-024-06534-x.

Jimenez, C. E. et al. (2024). *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* ICLR 2024.

Kretzer, F., Kolthoff, K., Bartelt, C., Ponzetto, S. P., and Maedche, A. (2025). *Closing the Loop between User Stories and GUI Prototypes: An LLM-Based Assistant for Cross-Functional Integration in Software Development*. CHI 2025. DOI: 10.1145/3706598.3713932.

Kwa, T. et al. (2025). *Measuring AI Ability to Complete Long Tasks*. arXiv:2503.14499.

Massenon, R., Gambo, I., and Khan, J. A. (2026). *Toward an Automated Cross-Multimodal Verification of Mobile App Bug Fixes*. Information and Software Technology 191, 107996. DOI: 10.1016/j.infsof.2025.107996.

Nass, M., Alegroth, E., and Feldt, R. (2021). *Why Many Challenges with GUI Test Automation (Will) Remain*. Information and Software Technology 138, 106625. DOI: 10.1016/j.infsof.2021.106625.

Wen, B. et al. (2025). *Know Your Limits: A Survey of Abstention in Large Language Models*. Transactions of the Association for Computational Linguistics 13, 529-556. DOI: 10.1162/tacl_a_00754.
