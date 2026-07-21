# Automated UI Requirement Verification from Ordered Screenshot Sequences

## First Draft: Introduction and Evaluation

**Status:** Working thesis prose, 15 July 2026. The quantitative results in this document are preliminary and cover a controlled subset of 201 verification items from flows 01–10. They must be replaced or confirmed after the final 258-item experiment is frozen and executed.

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

This motivates an evidence discipline: a requirement should not be marked `FULFILLED` unless all central observable parts are supported by visible evidence. Missing evidence alone should not be interpreted as a violation. `NOT_FULFILLED` is reserved for a central observable claim contradicted by the available UI states. If one part is supported while another is missing, hidden, or ambiguous, `PARTIALLY_FULFILLED` may be appropriate. If the screenshots cannot justify a reliable positive or negative decision, the verifier should `ABSTAIN`. This use of abstention follows the broader reject-option idea that a system may decline to make a concrete prediction when the available information is insufficient (Hendrickx et al., 2021; Wen et al., 2024).

The task also requires an explicit boundary between visible UI behavior and hidden system truth. This thesis does not attempt to prove backend correctness from screenshots. It does not infer security guarantees, actual payment processing, email delivery, database persistence, catalog completeness, long-term availability, or external real-world effects unless the requirement is explicitly limited to a visible UI representation of such a property. A success message may be evaluated as a visible success proxy; it does not prove that the underlying operation occurred correctly. This boundary is necessary for interpreting both predictions and reference labels consistently.

### 1.3 Research Gap and Approach

Existing work provides several parts of the technical context without directly solving this task. UI-agent datasets such as Mind2Web represent ordered interaction trajectories and have enabled research on language-conditioned action selection (Deng et al., 2023). GUI-grounding work such as SeeClick studies the localization of interface elements from language instructions (Cheng et al., 2024). Recent cross-modal software-verification research combines textual and visual artifacts to assess mobile-app bug fixes (Massenon et al., 2025). Requirements traceability research explains why links between statements and artifacts matter, while abstention research explains why a model should sometimes refuse a definite decision.

The setting considered here differs in its output contract. The goal is not to choose the next action, locate one instructed element, or determine whether a bug-fix pair is consistent. The verifier receives a textual requirement that may contain several obligations and an already recorded screenshot flow. It must determine what the flow establishes about that requirement, provide explicit evidence steps, and remain conservative about unobserved behavior. The ordering of screenshots matters because many obligations are expressed only through transitions: an action is selected on one screen and its result appears on a later screen.

The implemented prototype follows an evidence-first pipeline. First, screenshots are converted into lightweight screen representations using available metadata, text, OCR sidecars, or summaries. Second, the requirement is assessed for UI evaluability and may be decomposed into smaller claims. Third, an evidence retriever selects candidate screenshot steps for each claim. Fourth, a screenshot-grounded verifier assigns claim statuses and rationales. Finally, a deterministic aggregation policy converts those claim-level observations into a requirement-level label. Intermediate outputs are stored to make retrieval and reasoning errors separately inspectable.

The phrase “evidence-first” describes an architectural constraint, not a presupposed performance advantage. The verifier should select and inspect evidence before producing the final label. Whether this architecture improves accuracy or reduces unsafe fulfillment compared with a simpler whole-flow prompt is an empirical question. The preliminary results in this draft do not yet show such an improvement. Instead, they show that the explicit pipeline makes evidence quality measurable and exposes retrieval failures that would remain hidden behind a label-only score.

### 1.4 Research Questions

The thesis is organized around four research questions:

**RQ1: How accurately can multimodal models verify textual UI requirements from ordered screenshot flows?**

This question establishes the end-to-end difficulty of the task and compares model configurations using accuracy, macro-F1, per-class measures, and a safety-oriented false-fulfillment metric.

**RQ2: How does evidence-first verification affect label quality, false fulfillment, evidence traceability, and cost compared with whole-flow and deterministic baselines?**

This question tests the main architectural choices rather than assuming their benefit. It considers the trade-off between showing a model the complete flow and retrieving a smaller claim-specific subset. It also separates label correctness from whether the predicted evidence overlaps the human reference evidence.

**RQ3: Which requirement and evidence patterns cause the most frequent errors or abstentions?**

This question uses systematic error analysis to distinguish model bias, reasoning limitations, retrieval failures, and label-boundary disagreements. Particular attention is given to universal or comparative wording, late result states, hidden outcomes, and cross-step persistence claims.

**RQ4: As an exploratory question, how well does the approach transfer to structured PURE requirements?**

PURE contains public requirements documents whose requirements are typically longer and more dependent on document context than the requirements derived from UI trajectories (Ferrari, Spagnolo, and Gnesi, 2017). This question examines whether contextualized PURE requirements can be connected to available UI artifacts and which parts remain non-verifiable. It is explicitly secondary because the current PURE annotations are not yet mature enough for a final benchmark claim.

### 1.5 Contributions and Scope

The intended contributions of the thesis are:

1. **A problem formulation** for verifying textual UI requirements against ordered screenshot flows, including a separation between UI evaluability and fulfillment.
2. **An evidence-first prototype** that decomposes requirements, retrieves screenshot evidence, performs screenshot-grounded claim verification, and applies conservative aggregation.
3. **A reviewed benchmark** over 13 Mind2Web-derived flows containing requirement labels, claims, evidence steps, rationales, and uncertainty reasons, including contrastive items designed to avoid an overwhelmingly positive benchmark.
4. **An evaluation framework** that reports label quality, false fulfillment, abstention, coverage, evidence retrieval, claim matching, runtime, and cost rather than relying on accuracy alone.
5. **An empirical error analysis** of the requirement structures and flow patterns that produce unsafe or uncertain decisions.

The evaluated contribution is currently limited to screenshot-step evidence. Although the proposal discusses bounding boxes, the repository does not yet contain a mature region-localization evaluation. Bounding boxes must therefore be either implemented and evaluated before submission or described only as future work. Similarly, PURE is treated as exploratory external material unless its annotations receive independent review.

The thesis does not claim to establish industrial readiness or broad generalization from 13 flows. Its goal is to make the task and its failure modes measurable, to test several concrete verifier designs, and to identify what screenshots can and cannot support as requirement evidence.

Chapters 2–4—Background and Related Work, Problem Definition, and Approach—are planned in the accompanying roadmap but are not yet included in this prose draft. The draft continues with the dataset and evaluation chapters so that the current empirical basis can be reviewed early.

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

The current implementation can extract and contextualize selected PURE requirements and associate them with UI images embedded in or derived from the documents. However, the evaluation data is not final. The Split/Merge subset currently contains 29 verification items, of which only five are marked accepted and 24 still require review. Most annotations are recorded as Codex drafts. The Mashboot subset contains 11 post-hoc draft annotations created after the model output had been inspected. Mashboot therefore cannot be treated as blinded gold.

PURE can already support qualitative discussion about context dependence and UI verifiability. It cannot yet support a headline quantitative claim. Final inclusion requires independent review, a frozen extraction policy, and a clear explanation of how screenshots or document figures correspond to the intended system behavior.

## 6 Evaluation Design

### 6.1 Compared Systems

The preliminary controlled comparison covers flows 01–10 and 201 verification items. All compared configurations produce a prediction for every one of these items. Restricting every metric to the same 201-item denominator prevents missing flows from being silently counted as abstentions.

The first two configurations are whole-flow multimodal baselines. For each flow, the complete original screenshot set and all requirements are supplied in a single call. Each requirement is treated as one claim, so the comparison does not depend on automatic claim decomposition. The two model variants use Gemini 2.5 Flash Lite and Gemini 3.1 Pro.

The third configuration is the current evidence-first multimodal variant. It applies gated claim decomposition, lexical top-3 evidence retrieval, and batched screenshot verification with Gemini 2.5 Flash Lite. The retrieved evidence for claims is grouped to reduce repeated image uploads. In the current flows, the union of selected images can still be large; the method should therefore not be described as a strict per-claim three-image limit.

The fourth configuration is a deterministic evidence-first baseline. It uses gated claims and lexical top-3 retrieval but replaces the screenshot-grounded model with deterministic claim verification and aggregation. It provides a lower bound and tests how much performance depends on learned visual reasoning.

The final experiment should extend every configuration to flows 11–13 and add controlled ablations for claim decomposition, all screenshots versus top-k retrieval, and aggregation. Until that is done, the current table is a preliminary comparison, not the final answer to the research questions.

### 6.2 Label Metrics

Accuracy is the fraction of verification items whose predicted label equals the gold label. It is intuitive but insufficient under the current class distribution. A system that predicts `FULFILLED` for every item would already be correct on 66.7% of the full 258-item snapshot.

Macro-F1 calculates an F1 score independently for each of the four labels and averages them with equal weight. It therefore penalizes failure on `PARTIALLY_FULFILLED`, `NOT_FULFILLED`, or `ABSTAIN` even when those labels are uncommon. Weighted-F1 may be included as a secondary summary but inherits the influence of the majority class.

The false-fulfillment rate is defined as the fraction of predicted `FULFILLED` items whose gold label is not `FULFILLED`. This is a precision-oriented safety metric. It answers: when the system makes its strongest positive claim, how often is that claim too strong? The numerator includes gold partial, negative, and abstaining cases. The metric must be interpreted together with the number of predicted fulfilled items; a system could trivially reduce it by never predicting `FULFILLED`.

The abstain rate is the fraction of all predictions labeled `ABSTAIN`. Prediction coverage records the fraction of gold items for which an explicit model prediction exists. Missing predictions are not equivalent to model abstentions and must be reported separately. In the controlled 201-item comparison, coverage is 100% for all configurations.

### 6.3 Evidence Metrics

Evidence evaluation compares a ranked list of predicted screenshot steps with the human evidence steps. Hit@k is one if at least one gold evidence step occurs in the first k predicted steps and zero otherwise, averaged over items. Recall@k measures the fraction of all gold evidence steps retrieved in the first k positions. Precision@k measures how many predicted steps belong to the reference set. Mean reciprocal rank (MRR) rewards systems that place the first relevant step early.

These metrics capture different properties. A high hit@1 indicates that the system often finds at least one useful screenshot immediately. It does not show that all evidence required for a multi-step claim was retrieved. Recall is important when an action and its result occur on different screens or when a requirement contains several obligations. Evidence overlap also cannot determine whether the model interpreted the screenshot correctly; it measures trace alignment rather than semantic reasoning.

Comparable evidence metrics are currently available for the batched top-k and deterministic pipeline outputs. The whole-flow comparison files store evidence in a different comparison structure, and their evidence indexing must be normalized before a fair calculation. The absence of a comparable value must be reported as “not yet computed,” not as zero.

### 6.4 Claim Metrics and Qualitative Analysis

When predicted claims are available, they are matched to gold claims using text similarity before claim statuses are compared. Claim-match recall reports how many gold claims receive an acceptable predicted match. Claim-status macro-F1 then evaluates the status of matched claims. These metrics are sensitive to decomposition quality: a semantically valid split may use different wording or granularity from the gold annotation. Claim evaluation should therefore combine automatic matching with a manually inspected sample.

Qualitative error analysis assigns errors to recurring categories rather than treating them as unrelated mistakes. The main categories are over-fulfillment, anti-abstention, under-calling caused by missed evidence, and label-boundary disagreements. The analysis also records semantic patterns such as universal quantifiers, comparisons, result correctness, persistence, hidden system properties, and late cart or summary states.

## 7 Preliminary Results

### 7.1 Label Performance on Flows 01–10

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

The pipeline provides step-level evidence, not a mature bounding-box localization result. Screenshots cannot establish hidden backend truth, global absence, long-term persistence, external delivery, or complete result correctness. The current evidence-first configuration also does not yet improve false fulfillment over the whole-flow baseline. These are substantive findings and should not be hidden behind a general claim that evidence grounding automatically makes the model safer.

## 9 Preliminary Summary

The current evaluation shows that automated UI requirement verification from ordered screenshot flows is feasible but not solved. A strong whole-flow multimodal model reaches 81.1% preliminary accuracy on the controlled 201-item subset, while macro-F1 remains 0.573 because partial, negative, and abstaining cases are much harder than the majority fulfilled class. The evidence-first top-k pipeline makes screenshot traceability measurable and retrieves at least one reference evidence step within its top three results for 65.7% of items. However, it currently underperforms the whole-flow baseline on macro-F1 and false fulfillment.

The results support a measured thesis claim. Ordered screenshot flows provide a useful basis for visible UI verification, and claim/evidence structures expose where decisions depend on missing, hidden, or ambiguous information. The dominant problems are systematic rather than random: models over-generalize from partial visible cues, retrieval misses decisive late states, and screenshots cannot justify hidden outcomes. The contribution is therefore not a claim of production-ready verification. It is a problem formulation, implemented evidence pipeline, reviewed benchmark, and empirical analysis that makes these limitations observable and testable.

## References Used in This Draft

- Becker, J. et al. (2025). *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*. arXiv:2507.09089.
- Cheng, K. et al. (2024). *SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents*. ACL 2024. DOI: 10.18653/v1/2024.acl-long.505.
- Cleland-Huang, J. et al. (2014). *Software Traceability: Trends and Future Directions*. FOSE 2014. DOI: 10.1145/2593882.2593891.
- Deng, X. et al. (2023). *Mind2Web: Towards a Generalist Agent for the Web*. NeurIPS 2023. arXiv:2306.06070.
- Ferrari, A., Spagnolo, G. O., and Gnesi, S. (2017). *PURE: A Dataset of Public Requirements Documents*. IEEE RE 2017. DOI: 10.1109/RE.2017.29.
- Hendrickx, K. et al. (2021). *Machine Learning with a Reject Option: A Survey*. arXiv:2107.11277.
- Jimenez, C. E. et al. (2024). *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* ICLR 2024. arXiv:2310.06770.
- Kwa, T. et al. (2025). *Measuring AI Ability to Complete Long Tasks*. arXiv:2503.14499.
- Massenon, R. et al. (2025). *Toward an Automated Cross-Multimodal Verification of Mobile App Bug Fixes*. Information and Software Technology. DOI: 10.1016/j.infsof.2025.107996.
- Nass, M., Alégroth, E., and Feldt, R. (2021). *Why Many Challenges with GUI Test Automation (Will) Remain*. Information and Software Technology. DOI: 10.1016/j.infsof.2021.106625.
- Wen, B. et al. (2024). *Know Your Limits: A Survey of Abstention in Large Language Models*. arXiv:2407.18418.
