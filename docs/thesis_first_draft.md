# Automated UI Requirement Verification from Ordered Screenshot Sequences

## First Draft: Introduction and Evaluation

**Status:** Working thesis prose, updated 21 July 2026. The recommended final chapter structure is maintained in [`thesis_structure_and_bibliography_audit_2026-07-21.md`](thesis_structure_and_bibliography_audit_2026-07-21.md). Sections 6–7 below still document the useful historical 201-item controlled comparison; the current 258-item full-coverage snapshot is summarized in Section 9 and governed by [`thesis_evidence_audit.md`](thesis_evidence_audit.md).

## 1 Introduction

### 1.1 Motivation

Software development is increasingly shaped by generative and agentic artificial intelligence. Modern coding agents can inspect repositories, edit multiple files, execute tools, and iteratively respond to test results. Their capabilities have improved rapidly over the last several years. Kwa et al. (2025), for example, propose a task-completion time horizon that relates an agent's success to the time required by a human expert and report an approximately exponential historical increase on their studied software and reasoning tasks. Benchmarks such as SWE-bench have likewise moved evaluation from isolated code completion toward the resolution of real issues drawn from software repositories (Jimenez et al., 2024). These developments reduce the effort required to generate candidate implementations and make increasingly autonomous implementation workflows technically plausible.

This progress should not, however, be summarized as an unconditional increase in end-to-end software-engineering productivity. The effect depends on the task, the developer, the codebase, and the surrounding development process. In a randomized controlled trial with experienced open-source developers working on repositories they already knew, Becker et al. (2025) found that the early-2025 tools included in the study increased rather than reduced task completion time. The result does not negate the rapid growth of coding-agent capabilities, but it illustrates that generating code and delivering correct software are different outcomes. Repository context must be recovered, generated changes must match the intended behavior, and the result must be reviewed and verified.

The defensible motivation for this thesis is therefore a shift in relative engineering effort rather than the claim that implementation has universally become fast. As producing a candidate implementation becomes cheaper, other activities account for a larger share of the remaining work. Engineers still need to decide what the system should do, express that intent precisely, and determine whether the produced system actually conforms to it. Ambiguity in requirements can be amplified when an agent turns underspecified text into code without the tacit clarification that occurs in a human development team. Similarly, a high rate of generated changes can place additional pressure on review and verification. Requirements engineering and verification are thus not made obsolete by agentic coding. They become important control points for ensuring that faster implementation does not merely produce incorrect software faster.

User interfaces are a particularly relevant setting for this problem. Many software requirements are stated in natural language, whereas the corresponding implementation evidence is visual, interactive, and state-dependent. A requirement may ask that a menu be reachable without authentication, that a selected filter remain active, or that a cart summary display fees before checkout. None of these obligations is naturally represented by a single source-code location. Their satisfaction becomes visible through one or more interface states and through the transitions connecting those states.

This mismatch complicates both manual and automated verification. Manual inspection is flexible, but it is time-consuming and may be inconsistent across reviewers. Traditional GUI automation can execute precise interactions, but it usually depends on executable environments, selectors, stable test scripts, and explicit expected outcomes. These assumptions are difficult to maintain across heterogeneous real-world interfaces, and many practical challenges in GUI automation remain unresolved (Nass, Alégroth, and Feldt, 2021). Screenshot sequences occupy a useful intermediate point. They preserve concrete visual states and their order, can be inspected independently of a live deployment, and are available in existing interaction datasets. At the same time, they provide only partial observations: a recorded sequence shows what was visible during one trajectory, not every state the system could reach or every hidden property of the implementation.

### 1.2 Problem Statement

This thesis studies the following setting. The input consists of an ordered sequence of UI screenshots and a collection of textual requirements. For each requirement, the system should produce a verification label and point to the screenshot steps that justify its decision. The label set is `FULFILLED`, `PARTIALLY_FULFILLED`, `NOT_FULFILLED`, and `ABSTAIN`. The output may additionally contain smaller requirement claims, claim-level evidence statuses, uncertainty reasons, and a natural-language rationale.

The central difficulty is not merely multimodal classification. It is the disciplined construction of a trace link between a requirement and the available evidence. Traceability research has long emphasized the difficulty of connecting requirements to heterogeneous development artifacts (Cleland-Huang et al., 2014). In the present task, the target artifact is neither a code unit nor a test case. It is an ordered set of visible UI states. A useful verifier must identify which part of a requirement is observable, retrieve the relevant states, distinguish visible support from unsupported inference, and preserve uncertainty when the flow is insufficient.

A label-only model can fail in a particularly unsafe direction. Suppose that a screenshot shows a search form and a submit button. It is reasonable to conclude that the interface exposes search controls. It is not reasonable to conclude, without a result state, that the returned results are complete and correct. Similarly, a visible “remember me” control does not prove long-term persistence, and a menu link does not prove that every route-specific menu is applicable. A model that predicts `FULFILLED` from such partial evidence converts a plausible visual cue into a stronger claim than the screenshots establish.

This motivates an evidence discipline: a requirement should not be marked `FULFILLED` unless all central observable parts are supported by visible evidence. Missing evidence alone should not be interpreted as a violation. `NOT_FULFILLED` is reserved for a central observable claim contradicted by the available UI states. If one part is supported while another is missing, hidden, or ambiguous, `PARTIALLY_FULFILLED` may be appropriate. If the screenshots cannot justify a reliable positive or negative decision, the verifier should `ABSTAIN`. This use of abstention follows the broader reject-option idea that a system may decline to make a concrete prediction when the available information is insufficient (Hendrickx et al., 2024; Wen et al., 2025).

The task also requires an explicit boundary between visible UI behavior and hidden system truth. This thesis does not attempt to prove backend correctness from screenshots. It does not infer security guarantees, actual payment processing, email delivery, database persistence, catalog completeness, long-term availability, or external real-world effects unless the requirement is explicitly limited to a visible UI representation of such a property. A success message may be evaluated as a visible success proxy; it does not prove that the underlying operation occurred correctly. This boundary is necessary for interpreting both predictions and reference labels consistently.

### 1.3 Research Gap and Approach

Existing work provides several parts of the technical context without directly solving this task. Kretzer et al. (2025) connect user stories with GUI prototypes and study an assistant that detects whether a user story is represented in a prototype. UI-agent datasets such as Mind2Web represent ordered interaction trajectories and have enabled research on language-conditioned action selection (Deng et al., 2023). GUI-grounding work such as SeeClick studies the localization of interface elements from language instructions (Cheng et al., 2024). Recent cross-modal software-verification research combines textual and visual artifacts to assess mobile-app bug fixes (Massenon, Gambo, and Khan, 2026). Requirements traceability research explains why links between statements and artifacts matter, while abstention research explains why a model should sometimes refuse a definite decision.

The setting considered here differs in its output contract. The goal is not to choose the next action, locate one instructed element, or determine whether a bug-fix pair is consistent. The verifier receives a textual requirement that may contain several obligations and an already recorded screenshot flow. It must determine what the flow establishes about that requirement, provide explicit evidence steps, and remain conservative about unobserved behavior. The ordering of screenshots matters because many obligations are expressed only through transitions: an action is selected on one screen and its result appears on a later screen.

The implemented prototype follows an evidence-first pipeline. First, screenshots are converted into lightweight screen representations using available metadata, text, OCR sidecars, or summaries. Second, the requirement is assessed for UI evaluability and may be decomposed into smaller claims. Third, an evidence retriever selects candidate screenshot steps for each claim. Fourth, a screenshot-grounded verifier assigns claim statuses and rationales. Finally, a deterministic aggregation policy converts those claim-level observations into a requirement-level label. Intermediate outputs are stored to make retrieval and reasoning errors separately inspectable.

The phrase “evidence-first” describes an architectural constraint, not a presupposed performance advantage. The verifier should select and inspect evidence before producing the final label. Whether this architecture improves accuracy or reduces unsafe fulfillment compared with a simpler whole-flow prompt is an empirical question. The preliminary results in this draft do not yet show such an improvement. Instead, they show that the explicit pipeline makes evidence quality measurable and exposes retrieval failures that would remain hidden behind a label-only score.

### 1.4 Research Questions

The thesis is organized around three research questions:

**RQ1: How accurately can multimodal models apply a provided, application-specific verification label schema to UI-observable textual requirements using ordered screenshot flows?**

This question establishes the end-to-end difficulty of the task and explicitly evaluates whether the models follow the supplied four-label semantics rather than substituting a generic binary notion of success. It compares models using accuracy, macro-F1, per-class measures, confusion matrices, inter-model agreement, and a safety-oriented false-fulfillment metric.

**RQ2: How do claim decomposition and screenshot selection affect label accuracy, evidence traceability, and cost relative to direct whole-flow verification?**

This question tests the two main architectural factors rather than assuming their benefit. A controlled matrix compares raw requirements with automatic claim decomposition while independently comparing complete-flow input with a smaller claim-specific screenshot subset. Label correctness, evidence overlap, runtime, token usage, and monetary cost are reported separately.

**RQ3: Which requirement and evidence patterns cause verification errors, abstentions, or unsafe `FULFILLED` predictions?**

This question uses a predefined error taxonomy and systematic qualitative analysis to distinguish label-schema violations, reasoning limitations, retrieval failures, evidence insufficiency, and label-boundary disagreements. Particular attention is given to universal or comparative wording, late result states, hidden outcomes, and cross-step persistence claims. It characterizes observed abstentions; it does not claim that abstention causally improves safety.

### 1.5 Contributions and Scope

The intended contributions of the thesis are:

1. **A problem formulation** for verifying textual UI requirements against ordered screenshot flows, including a separation between UI evaluability and fulfillment.
2. **An evidence-first prototype** that decomposes requirements, retrieves screenshot evidence, performs screenshot-grounded claim verification, and applies conservative aggregation.
3. **A reviewed benchmark** over 13 Mind2Web-derived flows containing requirement labels, claims, evidence steps, rationales, and uncertainty reasons, including contrastive items designed to avoid an overwhelmingly positive benchmark.
4. **An evaluation framework** that reports label quality, false fulfillment, abstention, coverage, evidence retrieval, claim matching, runtime, and cost rather than relying on accuracy alone.
5. **An empirical error analysis** of the requirement structures and flow patterns that produce unsafe or uncertain decisions.

The mature evaluated contribution is currently limited to screenshot-step evidence. The repository now contains candidate-mark grounding runs over all 13 flows, but their generated regions have not received a prediction-independent relevance and sufficiency evaluation. Bounding boxes must therefore be either evaluated before submission or described as an exploratory implemented extension. PURE likewise remains exploratory because acceptance status does not remove its provenance and post-hoc-review limitations.

The thesis does not claim to establish industrial readiness or broad generalization from 13 flows. Its goal is to make the task and its failure modes measurable, to test several concrete verifier designs, and to identify what screenshots can and cannot support as requirement evidence.

Chapters 2–4—Foundations and Related Work, Research Design and Problem Formulation, and Verification Approach and Implementation—are planned in the accompanying roadmap but are not yet included in this prose draft. The draft continues with benchmark and evaluation material so that the empirical basis can be reviewed early.

## 5 Dataset and Annotation Methodology

### 5.1 Main Flow Dataset

The main evaluation data consists of 13 web interaction flows derived from the Mind2Web dataset. Mind2Web was originally introduced as a benchmark for generalist web agents and contains real website tasks and interaction trajectories (Deng et al., 2023). The present work does not reuse Mind2Web's original task as an action-prediction benchmark. Instead, it uses ordered screenshots from selected trajectories as observations against which independently represented UI requirements can be assessed.

The selected flows cover websites and tasks including theme-park purchases, product lookup, careers navigation, dining information, cinema support forms, cruise search, book search, and business listings. Their value for this thesis is the presence of multiple meaningful states. A cart flow, for example, may show product selection, quantity modification, add-ons, a summary, and checkout controls. A search flow may show inputs and later results. These ordered states make it possible to study requirements that cannot be resolved from one screenshot.

The current benchmark contains 258 verification items across the 13 flows. Of these, 173 originate from reviewed source requirements and 85 are reviewed contrastive verification items. The items contain 541 manually reviewed claims. Every verification item is currently marked accepted in the repository. This status means that the primary author completed the repository's review workflow. It does not mean that an independent second annotator agreed with the label.

The label distribution is imbalanced: 172 items are `FULFILLED`, 45 are `PARTIALLY_FULFILLED`, 33 are `ABSTAIN`, and 8 are `NOT_FULFILLED`. Approximately two thirds of the items are therefore positive. A classifier that favors `FULFILLED` can obtain a deceptively strong accuracy while failing on the three less frequent labels. This imbalance motivates macro-F1 and per-class reporting.

UI evaluability is annotated separately from fulfillment. The current set contains 192 `UI_VERIFIABLE`, 62 `PARTIALLY_UI_VERIFIABLE`, and 4 `NOT_UI_VERIFIABLE` items. This field answers whether screenshot evidence is capable in principle of resolving the requirement, while the final label answers what the recorded flow supports. A requirement can be UI-verifiable in principle but undecidable from a particular incomplete flow. Conversely, a compound requirement can have a visible part and a hidden part and therefore be only partially UI-verifiable.

### 5.2 From Candidates to Verification Gold

Requirements derived from a UI flow create a methodological risk. If a model generates a requirement that merely describes an obvious screenshot and a similar model later verifies it, the evaluation becomes self-fulfilling. The benchmark construction process addresses this risk through staged artifacts and human review.

The first stage contains harvested requirement hypotheses. These aim for breadth and may include redundancy, ambiguous wording, hidden properties, or requirements not fully supported by the flow. The second stage contains candidate requirements produced by filtering and rewriting. Candidate status does not imply correctness. A reviewer may reject the item, edit its wording, or promote it to the reviewed source set.

The 13 Mind2Web flows currently contain 100 committed candidate requirements and 173 reviewed source requirements. These counts refer only to the Mind2Web-derived directories; combining them with PURE candidates produces a different total and must be avoided in reporting. Review promotes a text into the source requirement set, but the verification benchmark adds further information: UI evaluability, a requirement-level label, atomic claims, claim statuses, evidence steps, rationale, and uncertainty reasons.

Contrastive requirements are used to increase difficulty and improve label coverage. A contrastive item may strengthen a visible requirement with a completeness condition, add a hidden persistence obligation, require a comparison that the flow does not show, or request a control that is visibly absent. The automatically proposed contrast and intended label are treated as suggestions. They become benchmark reference data only after review against the requirement wording and the screenshots.

This construction produces a more useful evaluation set than a collection of straightforward positive descriptions. It also introduces threats to validity. The source requirements are still derived from the same flows used for verification, the primary review was performed by one person, and the contrastive generation process may emphasize a particular family of hard cases. These limitations must be documented and partially mitigated through independent re-review, stratified reporting, and external material.

### 5.3 Annotation Schema

Each verification item contains a requirement-level decision and claim-level detail. The four requirement labels are interpreted as follows:

- `FULFILLED`: all central observable claims are visibly supported, no central claim is contradicted, and at least one evidence item is present.
- `PARTIALLY_FULFILLED`: at least one important claim is supported while another important claim is missing, hidden, or ambiguous, with no central visible contradiction that would justify a negative label.
- `NOT_FULFILLED`: a central observable claim is contradicted by visible evidence.
- `ABSTAIN`: the screenshots are insufficient for a reliable positive or negative decision, or the requirement primarily concerns non-visible properties.

Claims use statuses including `SUPPORTED`, `MISSING`, `CONTRADICTED`, `HIDDEN`, `AMBIGUOUS`, and `OUT_OF_SCOPE`. They are marked as core or supporting obligations and linked to screenshot steps. The claim layer is intended to expose why a compound requirement receives a partial or abstaining decision. It also creates a distinct evaluation problem: predicted claims may not have a one-to-one textual correspondence with gold claims and must be matched before their statuses are compared.

The evidence unit in the main evaluation is a screenshot step. Evidence-step annotation is less precise than a bounding box, but it is stable across the present data and directly represents the ordered-flow setting. A step annotation identifies which screen contains the observation; a textual evidence note describes the relevant visible content. Region-level grounding remains outside the current evaluated scope.

### 5.4 Running Example: Public Access to Amtrak Dining Information

The following requirement illustrates a clean positive case:

> The system shall make onboard dining information and café menu resources discoverable through public site navigation without requiring the user to sign in.

The requirement can be decomposed into two observable claims. First, onboard dining information and café menu resources are discoverable through public navigation. Second, the user is not required to sign in before reaching them. In the recorded flow, step 1 establishes the public site context, step 4 shows the Onboard Dining page and a route to the Café content, and step 5 shows the Café page and menu resources. The flow reaches these pages without displaying a sign-in wall. Both claims can therefore be supported by steps 1, 4, and 5.

The example is intentionally scoped to what the screenshots establish. A stronger requirement stating that route-specific menus are shown only when applicable would not be resolved by the same screenshots because no route context is visible. A requirement about account ownership checks would likewise refer to hidden access-control behavior. Small changes in wording can therefore change the correct label from `FULFILLED` to `PARTIALLY_FULFILLED` or `ABSTAIN`. This illustrates why requirement text, rather than the general intent imagined by the reviewer, must control the decision.

### 5.5 PURE as Exploratory External Material

PURE is a corpus of public requirements documents collected from heterogeneous sources and formats (Ferrari, Spagnolo, and Gnesi, 2017). Its documents are useful because their requirements are not generated from the screenshot trajectories used in the main benchmark. They are often longer, more formal, and dependent on headings, surrounding paragraphs, figures, or system context.

The current implementation can extract and contextualize selected PURE requirements and associate them with UI images embedded in or derived from the documents. The Split/Merge subset now contains 31 accepted verification items and 78 claims. Twenty-three items are attributed to Benno and eight retain Codex-draft provenance. The Mashboot subset contains 11 accepted items, but ten retain Codex-draft provenance and the annotation process began after predictions had been inspected. Acceptance status therefore does not make Mashboot blinded gold.

PURE can support qualitative discussion about context dependence, compound requirements, and UI verifiability. It cannot yet support a headline quantitative generalization claim. Some Split/Merge units are researcher-contextualized from descriptive document passages, and PURE figures usually express intended design rather than observed execution. Final inclusion requires provenance-aware reporting, independent review, a frozen extraction policy, and a clear distinction between document-to-UI consistency and implementation conformance.

## 6 Historical Evaluation Design

### 6.1 Compared Systems

This historical controlled comparison covers flows 01–10 and 201 verification items. All compared configurations produce a prediction for every one of these items. Restricting every metric to the same 201-item denominator prevents missing flows from being silently counted as abstentions. Newer 258-item full-coverage runs are now available, but they differ in multiple factors; the final evaluation chapter must present both the current snapshot and the remaining factor-controlled ablations.

The first two configurations are whole-flow multimodal baselines. For each flow, the complete original screenshot set and all requirements are supplied in a single call. Each requirement is treated as one claim, so the comparison does not depend on automatic claim decomposition. The two model variants use Gemini 2.5 Flash Lite and Gemini 3.1 Pro.

The third configuration is the current evidence-first multimodal variant. It applies gated claim decomposition, lexical top-3 evidence retrieval, and batched screenshot verification with Gemini 2.5 Flash Lite. The retrieved evidence for claims is grouped to reduce repeated image uploads. In the current flows, the union of selected images can still be large; the method should therefore not be described as a strict per-claim three-image limit.

The fourth configuration is a deterministic evidence-first baseline. It uses gated claims and lexical top-3 retrieval but replaces the screenshot-grounded model with deterministic claim verification and aggregation. It provides a lower bound and tests how much performance depends on learned visual reasoning.

The final experiment must freeze the benchmark and add controlled ablations for claim policy, all screenshots versus top-k retrieval, ordering, and aggregation. The current 258-item runs do not isolate these effects because their model, claim, retrieval, execution, and grounding choices differ.

### 6.2 Label Metrics

Accuracy is the fraction of verification items whose predicted label equals the gold label. It is intuitive but insufficient under the current class distribution. A system that predicts `FULFILLED` for every item would already be correct on 66.7% of the full 258-item snapshot.

Macro-F1 calculates an F1 score independently for each of the four labels and averages them with equal weight. It therefore penalizes failure on `PARTIALLY_FULFILLED`, `NOT_FULFILLED`, or `ABSTAIN` even when those labels are uncommon. Weighted-F1 may be included as a secondary summary but inherits the influence of the majority class.

The false-fulfillment rate is defined as the fraction of predicted `FULFILLED` items whose gold label is not `FULFILLED`. This is a precision-oriented safety metric. It answers: when the system makes its strongest positive claim, how often is that claim too strong? The numerator includes gold partial, negative, and abstaining cases. The metric must be interpreted together with the number of predicted fulfilled items; a system could trivially reduce it by never predicting `FULFILLED`.

The abstain rate is the fraction of all predictions labeled `ABSTAIN`. Prediction coverage records the fraction of gold items for which an explicit model prediction exists. Missing predictions are not equivalent to model abstentions and must be reported separately. In the controlled 201-item comparison, coverage is 100% for all configurations.

### 6.3 Evidence Metrics

Evidence evaluation compares a ranked list of predicted screenshot steps with the human evidence steps. Hit@k is one if at least one gold evidence step occurs in the first k predicted steps and zero otherwise, averaged over items. Recall@k measures the fraction of all gold evidence steps retrieved in the first k positions. Precision@k measures how many predicted steps belong to the reference set. Mean reciprocal rank (MRR) rewards systems that place the first relevant step early.

These metrics capture different properties. A high hit@1 indicates that the system often finds at least one useful screenshot immediately. It does not show that all evidence required for a multi-step claim was retrieved. Recall is important when an action and its result occur on different screens or when a requirement contains several obligations. Evidence overlap also cannot determine whether the model interpreted the screenshot correctly; it measures trace alignment rather than semantic reasoning.

The historical 201-item files provide directly comparable evidence metrics only for the batched top-k and deterministic outputs. Newer 258-item evaluators normalize screenshot-step evidence for all three current model configurations. Evidence tables must therefore identify the exact run and benchmark rather than mixing the two generations of artifacts.

### 6.4 Claim Metrics and Qualitative Analysis

When predicted claims are available, they are matched to gold claims using text similarity before claim statuses are compared. Claim-match recall reports how many gold claims receive an acceptable predicted match. Claim-status macro-F1 then evaluates the status of matched claims. These metrics are sensitive to decomposition quality: a semantically valid split may use different wording or granularity from the gold annotation. Claim evaluation should therefore combine automatic matching with a manually inspected sample.

Qualitative error analysis assigns errors to recurring categories rather than treating them as unrelated mistakes. The main categories are over-fulfillment, anti-abstention, under-calling caused by missed evidence, and label-boundary disagreements. The analysis also records semantic patterns such as universal quantifiers, comparisons, result correctness, persistence, hidden system properties, and late cart or summary states.

## 7 Historical Preliminary Results

### 7.1 Historical Label Performance on Flows 01–10

Table 1 reports the controlled preliminary comparison. Every row uses the same 201 verification items from flows 01–10 and 100% prediction coverage.

**Table 1: Preliminary label results on 201 items from flows 01–10.**

| Model/configuration | Evidence strategy | Accuracy | Macro-F1 | False fulfillment | Coverage | Estimated API cost |
|---|---|---:|---:|---:|---:|---:|
| Gemini 2.5 Flash Lite whole-flow | Original screenshots, one call per flow | 0.761 | 0.480 | 0.124 | 1.000 | $0.0138 |
| Gemini 3.1 Pro whole-flow | Original screenshots, one call per flow | 0.811 | 0.573 | 0.099 | 1.000 | $0.8401 |
| Gemini 2.5 Flash Lite batched top-k | Gated claims, lexical top-3, batched verification | 0.751 | 0.387 | 0.215 | 1.000 | $0.0221 |
| Deterministic baseline | Gated claims, lexical top-3, deterministic verification | 0.204 | 0.136 | 0.455 | 1.000 | — |

Gemini 3.1 Pro achieves the highest preliminary accuracy and macro-F1. Its advantage over Flash Lite whole-flow is approximately five percentage points in accuracy and 0.093 in macro-F1. It also has the lowest false-fulfillment rate among the four configurations. This gain comes with a substantial cost difference: the recorded estimated cost for Pro is approximately 61 times the whole-flow Flash Lite estimate. The cost calculation depends on the pricing assumptions stored with the run and should be updated for the final experiment.

The whole-flow Flash Lite baseline slightly outperforms the batched top-k variant in accuracy and substantially outperforms it in macro-F1 and false fulfillment. The current evidence-first configuration therefore does not demonstrate the expected reduction in unsafe positive decisions. It predicts `FULFILLED` too often when retrieved screenshots provide only partial support. Evidence gating prevents a positive label without any cited screen, but it cannot ensure that the cited screen proves every core obligation if the claim verifier interprets the evidence too generously.

The deterministic baseline performs poorly. Its abstain rate is approximately 0.771, yet 45.5% of the items it does label `FULFILLED` are not fulfilled according to gold. This combination shows that conservative aggregation alone is insufficient when claim statuses are weak. The system needs both reliable evidence selection and reliable semantic interpretation.

The macro-F1 values are considerably lower than the corresponding accuracies because the minority classes remain difficult. In the batched top-k run, for example, the system performs strongly on `FULFILLED` but almost never predicts `NOT_FULFILLED` and has low recall for `PARTIALLY_FULFILLED`. The final thesis must show the full confusion matrix and per-class precision and recall rather than only the four aggregate columns in Table 1.

### 7.2 Evidence Retrieval

Table 2 reports evidence metrics for the two configurations that currently have directly comparable step-level outputs.

**Table 2: Preliminary evidence retrieval results on 201 items from flows 01–10.**

| Configuration | MRR | Hit@1 | Hit@3 | Recall@1 | Recall@3 |
|---|---:|---:|---:|---:|---:|
| Gemini Flash Lite batched top-k | 0.582 | 0.473 | 0.657 | 0.260 | 0.485 |
| Deterministic baseline | 0.159 | 0.159 | 0.159 | 0.076 | 0.076 |

The batched top-k pipeline retrieves at least one gold evidence step in its first three predictions for approximately 65.7% of the items. Recall@3 is lower, at 48.5%, indicating that many multi-step evidence sets are incomplete even when one relevant screen is found. This distinction is important: verification may require a control state and a later result state, while hit@k is satisfied by retrieving either one.

The evidence results support the use of retrieval as a separately measurable component. They do not yet establish that top-k improves the final label. In fact, the current label results are weaker than the whole-flow baseline. Retrieval can help by concentrating model attention and reducing repeated image input, but it also creates a failure mode that the whole-flow prompt avoids: a decisive screenshot may never reach the verifier.

### 7.3 Dominant Error Patterns

The historical 13-flow review and the controlled runs reveal several recurring patterns. Exact category counts from the historical reports should not be mixed with the final controlled metrics because the underlying runs and gold snapshot changed. The patterns themselves are stable enough to guide the final analysis.

**Over-fulfillment.** The verifier frequently treats evidence for a visible entry point as evidence for the complete requirement. A search form becomes proof of correct search results, a link becomes proof of correct applicability, or one observed path becomes proof of a universal condition. This error directly increases false fulfillment.

**Hidden and external outcomes.** Requirements concerning persistence, availability, validity, delivery, payment, security, or backend correctness cannot usually be decided from the recorded screenshots. Models nevertheless prefer concrete labels and may infer an outcome from a UI proxy. The aggregation policy should preserve `HIDDEN` or `AMBIGUOUS` claim statuses and abstain when the hidden obligation is central.

**Universal and comparative language.** Terms such as “all,” “every,” “only,” and “always” require evidence across a defined domain. A finite flow often shows only one instance. Comparisons require both sides or a visible invariant across relevant states. The model tends to generalize beyond the observed example.

**Missing late states.** Cart, checkout, result, review, and summary evidence often appears near the end of a flow. A retriever dominated by lexical overlap may select an earlier screen containing the requirement vocabulary but omit the later screen that demonstrates the outcome.

**Boundary disagreements.** Some cases depend on the distinction between `PARTIALLY_FULFILLED` and `ABSTAIN`, or between `NOT_FULFILLED` and `ABSTAIN`. The adopted policy requires visible contradiction for `NOT_FULFILLED`. If a requested result state is not shown at all, abstention may be safer than a negative conclusion. If a visible entry point is supported but the result is unobserved, partial fulfillment may be more informative. These boundaries require explicit examples in the annotation guide and independent adjudication.

### 7.4 Late-State Failure Example

The Six Flags purchase flow (flow 10) provides a representative retrieval failure. Several requirements refer to quantity changes, combined cart contents, fees and totals, the ability to modify the cart, and controls visible before purchase confirmation. The decisive evidence appears in late steps, especially steps 8–10. Earlier evidence-selection variants often retrieved configuration or add-on screens but did not include the final cart summary.

This failure is not primarily a lack of visual intelligence. If the final cart screenshot is not supplied, the verifier cannot cite its subtotal, fee, tax, total, or modify-cart control. The resulting prediction may be `ABSTAIN` or `PARTIALLY_FULFILLED` even though the relevant visible state exists in the full flow. The example motivates retrieval rules that include action/result pairs, prioritize late screens for state-change requirements, or dynamically fall back to the whole flow when retrieved evidence is insufficient.

At the same time, always attaching the complete flow is not a free solution. Long flows increase image input, cost, and the amount of irrelevant content the model must inspect. The final evaluation should therefore treat retrieval as a trade-off among label quality, evidence recall, cost, and traceability rather than assuming that smaller top-k values are inherently better.

### 7.5 Current Controlled Full-Benchmark Comparison

The primary RQ2 matrix was completed on 23 July 2026 after the historical analysis above. It uses the same 258 accepted items from flows 01–13, Gemini 3.1 Flash-Lite, prompt version, label schema, aggregation, and execution parameters in every cell. Only claim policy and screenshot policy vary. All four cells have 100% prediction coverage and no recorded fallbacks or failures.

| Claim policy | Screenshot policy | Accuracy | Macro-F1 | False fulfillment | Abstain | Evidence MRR | Estimated cost |
|---|---|---:|---:|---:|---:|---:|---:|
| Raw requirements | All screenshots | 0.795 | 0.514 | 0.106 | 0.190 | 0.716 | $0.2817 |
| Gated automatic decomposition | All screenshots | 0.791 | 0.536 | 0.124 | 0.171 | 0.734 | $0.3002 |
| Raw requirements | Lexical top-4 | 0.713 | 0.387 | 0.110 | 0.279 | 0.621 | $0.2778 |
| Gated automatic decomposition | Lexical top-4 | 0.736 | 0.518 | 0.104 | 0.260 | 0.607 | $0.2394 |

The result is mixed. A paired 10,000-sample percentile bootstrap resampling the 13 complete flows gives a 95% interval of -12.0 to -3.8 percentage points for the raw top-4 versus raw/all accuracy difference and -0.244 to -0.043 for macro-F1. Its MRR difference also has an interval below zero. Restricting raw requirements to four screenshots therefore loses measurable information while reducing estimated cost by less than half a cent. The present batching strategy repeats selected screenshots across calls, and reduced image input is partly offset by output and thinking tokens.

Automatic gated decomposition does not consistently improve accuracy, false fulfillment, or screenshot-step evidence ranking. With all screenshots, its accuracy and macro-F1 difference intervals span zero, while false fulfillment increases by 1.9 percentage points with a 95% interval from +0.4 to +3.3. Under top-4 evidence, decomposition improves macro-F1 by 0.131 with an interval from +0.021 to +0.193, suggesting an interaction between requirement granularity and restricted evidence. With only 13 resampled clusters, these intervals must still be interpreted cautiously.

An offline policy counterfactual replaced every native `ABSTAIN` with `NOT_FULFILLED` without making new model calls. Accuracy fell from 0.795 to 0.702 for raw/all and from 0.736 to 0.643 for gated/top-4; macro-F1 fell to 0.331 and 0.305. False fulfillment was unchanged because the policy cannot generate a positive label. The result shows that treating absence of sufficient evidence as a negative verdict is harmful on this benchmark. It does not show that every abstention is calibrated or that abstention causally reduces unsafe positive predictions.

### 7.6 Run-to-Run Stability

Two independent repetitions were executed for the raw/all and gated/top-4
Gemini anchors and for the hosted Qwen raw/shared-top-4 baseline. Every
repetition covered all 13 flows and 258 items. The new Gemini runs used 160
first-attempt API calls without cache hits, fallbacks, or failures; the Qwen
runs used 78 first-attempt calls, were served by Alibaba with provider fallbacks
disabled, and likewise recorded no failures.

Gemini produced exactly the same requirement label for every item in all three
executions of both configurations. Raw/all therefore remains at 0.795 accuracy
and 0.514 macro-F1 in every run, while gated/top-4 remains at 0.736 accuracy and
0.518 macro-F1. Screenshot-step evidence was not perfectly invariant: raw/all
evidence MRR ranges from 0.712 to 0.716 and gated/top-4 from 0.607 to 0.610.

Qwen shows small but measurable variation. Across three executions, accuracy
ranges from 0.705 to 0.713, macro-F1 from 0.345 to 0.356, false fulfillment from
0.185 to 0.189, and evidence MRR from 0.622 to 0.635. Pairwise label agreement
ranges from 0.965 to 0.988, with Cohen's kappa between 0.906 and 0.969. These
figures indicate strong descriptive stability without implying determinism or
treating repeated executions on the same benchmark as independent samples.

The six repetitions cost approximately USD 1.1245 in recorded successful
inference usage. Bounding boxes were not requested in the Qwen runs. The Gemini
prompt did produce unvalidated free-form visual regions, but the mature
evaluated evidence contribution remains screenshot-step traceability.

The matched raw/all comparison also provides a model-sensitivity result for RQ1. Gemini 3.1 Flash-Lite reaches 79.5% accuracy compared with 73.3% for Gemini 2.5 Flash-Lite. The paired flow-cluster bootstrap estimates an accuracy difference of 6.2 percentage points with a 95% interval from 1.6 to 10.8. The models assign the same label to 83.3% of items; Cohen's kappa is 0.616.

A separate hosted open-weight baseline compares Qwen3-VL-8B-Instruct with Gemini 3.1 Flash-Lite under the same raw-requirement, batched shared-top-4 evidence condition. Both reach 71.3% accuracy and essentially identical evidence MRR (0.622 and 0.621). Their label agreement is 81.0% and Cohen's kappa is 0.559. The equality in accuracy hides a safety-relevant difference: Qwen's false-fulfillment rate is 18.5%, 7.4 percentage points above Flash-Lite (flow-cluster bootstrap 95% interval +2.5 to +12.6), and its macro-F1 is lower at 0.356. This comparison supports cross-provider model sensitivity while showing that headline accuracy alone is insufficient. Qwen was accessed through OpenRouter on Alibaba infrastructure; its Apache-2.0 weights are available, but the hosted serving stack and quantization remain opaque.

## 8 Limitations and Threats to Validity

### 8.1 Internal Validity

All current Mind2Web verification items were reviewed by the primary author. Although the items are marked accepted, no inter-annotator agreement has been measured. Requirement labels, claim boundaries, and evidence sets may therefore reflect one reviewer's interpretation. A second reviewer should independently annotate a stratified sample covering all labels and major ambiguity categories. Disagreements should be adjudicated before the final runs.

The requirements are derived from the same flows against which they are evaluated. Human review and contrastive items reduce but do not eliminate circularity. Generated requirements may still emphasize properties that are easy to see in the source flow or mirror the assumptions of the generation model. Separate results for original and contrastive requirements and the exploratory PURE comparison can make this limitation more visible.

Model outputs are sensitive to model version, prompt text, image preparation, retries, and aggregation. Historical repository reports combine different current-per-flow runs and are useful for diagnosis but not controlled comparison. Final experiments require an immutable run manifest and exact model identifiers.

### 8.2 Construct Validity

The four labels operationalize a conservative interpretation of screenshot-based verification. Other projects might define missing evidence as failure or treat visible success messages as sufficient proof of a backend outcome. The thesis must present its label policy as a deliberate construct tied to the intended safety goal, not as the only possible definition.

Screenshot-step overlap is an incomplete measure of evidence quality. Human annotations may contain several valid screens, and a prediction may cite a semantically valid alternative that is absent from the reference set. Conversely, retrieving a gold step does not prove that the model used the correct region or interpretation. Manual evidence inspection should complement the automated metrics.

Claim matching introduces additional uncertainty. Two decompositions can be semantically equivalent while using different granularity. Low claim-status performance may reflect a poor decomposition, poor text matching, or poor status prediction. The final report should separate claim-match recall from status quality on matched claims.

### 8.3 External Validity

Thirteen web flows are a small sample of the variety of real interfaces and requirements. The selected tasks do not establish generalization to native mobile applications, desktop software, accessibility requirements, or industrial specifications. Mind2Web trajectories reflect one recorded interaction path and may omit alternative states relevant to a requirement.

PURE provides more realistic requirement documents but introduces a different limitation: screenshots or UI figures included in a requirements document typically describe intended behavior rather than observations of a running implementation. Verification against such figures may therefore assess document consistency rather than implementation conformance. The difference must be explicit if PURE is retained.

### 8.4 Reliability and Reproducibility

Model APIs can return malformed responses, change behavior between versions, or fail transiently. Older flow runs contained API fallbacks, and cached responses may hide differences between repeated executions. Final reporting should include retries, failures, fallbacks, token counts, image counts, runtime, cache policy, and pricing assumptions.

The repository contains stale summary metrics generated against older benchmark snapshots. For example, one stored batched-top-k metric reports 31.8% accuracy because it evaluates 201 predictions against all 258 current gold items and counts the 57 absent predictions as abstentions. Recomputed metrics restricted to the actual 201-item run give 75.1% accuracy. This discrepancy demonstrates why each thesis table must be generated from a frozen manifest with matching prediction and gold sets.

### 8.5 Current Scope Limitations

The pipeline provides mature step-level evidence and implemented but not yet human-validated region grounding. Screenshots cannot establish hidden backend truth, global absence, long-term persistence, external delivery, or complete result correctness. The completed 2x2 matrix isolates claim and screenshot policy for one model, but it does not show that evidence-first design uniformly improves false fulfillment. These are substantive boundaries and should not be hidden behind a general claim that evidence grounding automatically makes the model safer.

### 8.6 Dataset Licensing and Artifact Availability

All 13 primary flows belong to the Mind2Web `test_task` split. Mind2Web is
identified by its maintainers as CC BY 4.0, but the official repository also
asks users not to redistribute unzipped test files online and not to place
benchmark data in training corpora. The public replication artifact is
therefore restricted to code, configurations, citations, and aggregate results.
It excludes original screenshots, HTML, MHTML, HAR files, traces, videos,
processed trajectories, test records, and per-item raw model interactions.
Exact test identifiers and detailed annotations remain available only for
examination under controlled access unless the maintainers approve broader
release.

PURE has a different rights limitation. Its curators collected requirements
documents from third-party Web sources and explicitly state that they are not
aware of license agreements or intellectual-property rights governing the
source requirements. Consequently, the public artifact excludes PURE PDFs, XML
files, extracted figures, substantial text passages, and per-item outputs that
reproduce those passages. It may contain document identifiers, hashes,
author-created non-textual labels, aggregate metrics, and code that requires
users to obtain PURE independently. These conservative boundaries support
replication without asserting rights over third-party source content.

## 9 Current Preliminary Summary

The current evaluation shows that automated UI requirement verification from ordered screenshot flows is feasible but not solved. In the controlled 258-item Gemini 3.1 Flash-Lite matrix, raw requirements with the complete screenshot flow reach 79.5% accuracy and 0.514 macro-F1. Gated automatic decomposition with all screenshots reaches 79.1% accuracy and 0.536 macro-F1. Restricting evidence to lexical top-4 lowers accuracy to 71.3% for raw requirements and 73.6% for gated decomposition. The effects of decomposition are metric-dependent, while top-4 selection clearly loses information and produces almost no cost saving in the current implementation.

The results support a measured thesis claim. Ordered screenshot flows provide a useful basis for visible UI verification, and claim/evidence structures expose where decisions depend on missing, hidden, or ambiguous information. The dominant problems are systematic rather than random: models over-generalize from partial visible cues, retrieval misses decisive late states, and screenshots cannot justify hidden outcomes. The contribution is therefore not a claim of production-ready verification. It is a problem formulation, implemented evidence pipeline, reviewed benchmark, and empirical analysis that makes these limitations observable and testable.

## References Used in This Draft

- Becker, J. et al. (2025). *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*. arXiv:2507.09089.
- Cheng, K. et al. (2024). *SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents*. ACL 2024. DOI: 10.18653/v1/2024.acl-long.505.
- Cleland-Huang, J. et al. (2014). *Software Traceability: Trends and Future Directions*. FOSE 2014. DOI: 10.1145/2593882.2593891.
- Deng, X. et al. (2023). *Mind2Web: Towards a Generalist Agent for the Web*. NeurIPS 2023. arXiv:2306.06070.
- Ferrari, A., Spagnolo, G. O., and Gnesi, S. (2017). *PURE: A Dataset of Public Requirements Documents*. IEEE RE 2017. DOI: 10.1109/RE.2017.29. Current dataset record: 10.5281/zenodo.7118517; original archived version: 10.5281/zenodo.1414117.
- Hendrickx, K. et al. (2024). *Machine Learning with a Reject Option: A Survey*. Machine Learning 113, 3073–3110. DOI: 10.1007/s10994-024-06534-x.
- Jimenez, C. E. et al. (2024). *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* ICLR 2024. arXiv:2310.06770.
- Kretzer, F., Kolthoff, K., Bartelt, C., Ponzetto, S. P., and Maedche, A. (2025). *Closing the Loop between User Stories and GUI Prototypes: An LLM-Based Assistant for Cross-Functional Integration in Software Development*. CHI 2025, Article 879. DOI: 10.1145/3706598.3713932.
- Kwa, T. et al. (2025). *Measuring AI Ability to Complete Long Tasks*. arXiv:2503.14499.
- Massenon, R., Gambo, I., and Khan, J. A. (2026). *Toward an Automated Cross-Multimodal Verification of Mobile App Bug Fixes*. Information and Software Technology 191, 107996. DOI: 10.1016/j.infsof.2025.107996.
- Nass, M., Alégroth, E., and Feldt, R. (2021). *Why Many Challenges with GUI Test Automation (Will) Remain*. Information and Software Technology. DOI: 10.1016/j.infsof.2021.106625.
- Wen, B. et al. (2025). *Know Your Limits: A Survey of Abstention in Large Language Models*. Transactions of the Association for Computational Linguistics 13, 529–556. DOI: 10.1162/tacl_a_00754.
