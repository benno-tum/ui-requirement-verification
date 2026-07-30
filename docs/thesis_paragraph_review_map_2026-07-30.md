# Thesis Paragraph Review Map

**Snapshot:** `docs/thesis_first_draft.md` after the 30 July 2026 revisions
**Purpose:** Compact meeting and revision aid. This map summarizes each prose
paragraph, states its function, and indicates how it connects to the surrounding
argument. Source line numbers refer to this snapshot and will move after later
edits.

Lists, equations, tables, quotations, and non-rendered comments are treated as
structural units attached to the prose paragraph that introduces or interprets
them. Reference-list entries are not summarized individually.

## Fast Meeting Agenda

1. **Research-question alignment:** RQ1 now covers written requirements and
   ordered UI screenshot sequences. RQ2 is supported by the controlled 2x2
   matrix. RQ3 still uses the causal verb “cause,” although its analysis is
   descriptive.
2. **Benchmark interpretation:** The primary benchmark reconstructs source
   requirements from observed flows. It evaluates evidence interpretation but
   not defect detection against independent, requirements-first specifications.
3. **Evidence sufficiency:** The four verdicts do not completely specify when a
   visible UI cue is strong enough. The discussion proposes a future layered
   evidence-sufficiency rubric.
4. **Final-result readiness:** UI-evaluability and region-grounding sections are
   still explicitly preliminary and contain pending-review boundaries.
5. **Chapter 6 length:** Development-stage results, current results, stability,
   chronology, UI evaluability, and grounding are all retained. Decide whether
   development history belongs in the final main text or an appendix.
6. **Final-prose cleanup:** A few paragraphs still use drafting language such as
   “the final thesis must” or “the final report should.”

## Reading Template

Each entry follows:

> **Pxxx (source lines)** — Core idea. *Role/link:* function in the argument and
> connection to the next paragraph or section.

## Draft Status Note

- **P001 (5–11)** — Declares the document a working draft and identifies pending
  UI-evaluability and grounding reviews. *Role/link:* establishes which claims
  are frozen and directs quantitative disputes to the evidence audit.

## 1 Introduction

### 1.1 Motivation

- **P002 (17)** — Coding agents now perform repository-scale work, and benchmark
  capability has grown quickly. *Role/link:* establishes technological relevance;
  P003 checks whether capability translates into productivity.
- **P003 (19–25)** — Real developer productivity does not automatically follow
  benchmark progress, and generated changes still require verification.
  *Role/link:* prevents an inflated AI-progress premise; P004 narrows the thesis
  motivation.
- **P004 (27–34)** — Cheaper candidate implementation shifts relative effort
  toward requirements clarification and verification. *Role/link:* derives the
  practical need for the thesis without claiming universal productivity gains.
- **P005 (36–41)** — UI requirements make the contract/evidence modality gap
  concrete because behavior appears in visible states and transitions.
  *Role/link:* selects the UI domain; P006 motivates screenshot sequences.
- **P006 (43–51)** — Manual and conventional GUI testing have practical limits;
  recorded screenshot sequences are inspectable but incomplete evidence.
  *Role/link:* introduces the thesis’s evidence medium and its central limitation.

### 1.2 Problem Statement

- **P007 (55)** — Defines the input, four-label output, evidence steps, optional
  claims, rationales, and regions. *Role/link:* states the complete task contract.
- **P008 (57–65)** — Frames the task as constructing a trace from requirements to
  fixed visual evidence while controlling inference. *Role/link:* distinguishes
  the problem from generic multimodal classification.
- **P009 (67–73)** — The eGift-card example separates a visible action control
  from an unobserved result. *Role/link:* gives an intuitive boundary case for the
  label policy in P010.
- **P010 (75–82)** — Defines the practical distinction among fulfilled, partial,
  negative, and abstaining decisions. *Role/link:* turns the example into the
  evidence-bounded verdict policy.
- **P011 (84–90)** — Hidden backend and external properties remain outside
  screenshot evidence unless only their visible representation is required.
  *Role/link:* closes the problem definition with the visible/hidden boundary.

### 1.3 Research Gap and Approach

- **P012 (94)** — Positions the thesis among prototype traceability, GUISpector,
  Mind2Web, GUI grounding, bug-fix verification, and abstention work.
  *Role/link:* establishes neighboring literature; P013 isolates the gap.
- **P013 (96–103)** — The fixed, incomplete evidence record and four-label
  contract distinguish the task from exploration, action selection, and element
  localization. *Role/link:* states the research gap and why screenshot order
  matters.
- **P014 (105–110)** — Summarizes the implemented stages from screen
  representation through deterministic aggregation. *Role/link:* connects the gap
  to the evaluated system design.
- **P015 (112–116)** — “Evidence-first” is a diagnostic architecture, not an
  assumed accuracy advantage. *Role/link:* states the central empirical stance
  before the research questions.

### 1.4 Research Questions

- **P016 (120)** — Announces three research questions. *Role/link:* transitions
  from motivation and gap to the evaluation plan.
- **P017 (122)** — RQ1 asks how well multimodal models determine fulfillment
  status from ordered UI screenshot sequences. *Role/link:* defines the end-to-end
  performance question.
- **P018 (124–127)** — Maps RQ1 to the fixed four-label operationalization and its
  metrics. *Role/link:* makes “how well” measurable.
- **P019 (129)** — RQ2 asks how decomposition and screenshot selection affect
  labels, traceability, and cost. *Role/link:* defines the controlled architecture
  comparison.
- **P020 (131–134)** — Maps RQ2 to the raw/decomposed by all/top-4 matrix and
  separate outcome measures. *Role/link:* states the experimental factors and
  measurements.
- **P021 (136)** — RQ3 asks which patterns cause errors, abstentions, and unsafe
  fulfilled predictions. *Role/link:* defines the qualitative error question;
  “cause” remains stronger than the descriptive design supports.
- **P022 (138–142)** — Maps RQ3 to the frozen taxonomy and explicitly avoids a
  causal safety claim for abstention. *Role/link:* partially limits the causal
  wording used in RQ3.

### 1.5 Contributions and Scope

- **P023 (146)** — Introduces the five-item contribution list. *Role/link:* the
  following list claims a formulation, prototype, benchmark, evaluation
  framework, and error analysis.
- **P024 (162–170)** — Separates screenshot-step and region evidence, keeps
  grounding outside accuracy claims, and isolates PURE from the main benchmark.
  *Role/link:* prevents traceability contributions from being overstated.
- **P025 (172–175)** — Limits claims to 13 flows and positions the contribution as
  making the task and failures measurable. *Role/link:* gives the high-level
  empirical boundary.
- **P026 (177–180)** — Provides the chapter roadmap. *Role/link:* closes the
  introduction and hands off to foundations.

## 2 Foundations and Related Work

### Literature-Search Documentation

- **P027 (184–187)** — Introduces the dated Google Scholar search and its four
  concept blocks. *Role/link:* documents how the closest cross-artifact work was
  located.
- **P028 (189–193)** — Presents the exact query combining software artifacts,
  GUI artifacts, relation terms, and multimodal models. *Role/link:* makes the
  search reproducible.
- **P029 (195–210)** — Justifies traceability, consistency, and conformance;
  records result count, screening method, exclusions, and the three closest
  papers. *Role/link:* bounds the targeted search and introduces the broader
  supporting literatures.

### 2.1 Requirements as Verification Contracts

- **P030 (214–221)** — Requirements define obligations and coordinate design,
  implementation, and testing. *Role/link:* establishes the written requirement
  as the verification contract.
- **P031 (223–232)** — Natural-language flexibility creates ambiguity that UI
  inspection cannot resolve. *Role/link:* explains why evidence alone cannot
  repair an underspecified contract.
- **P032 (234–243)** — Quantifiers are preserved but evaluated over their stated
  and visibly bounded domain; bounded coverage can support fulfillment, whereas
  unresolved scope blocks fulfillment without becoming a negative verdict.
  *Role/link:* defines the semantic discipline applied in annotation and
  prediction.
- **P033 (241–249)** — UI obligations may require single states or ordered
  transitions. *Role/link:* connects requirements semantics to the need for
  screenshot sequences.

### 2.2 Requirements Traceability

- **P034 (253–260)** — Extends classical traceability from code and tests to
  visible UI states. *Role/link:* establishes evidence links as a contribution.
- **P035 (262–267)** — Lexical overlap is neither necessary nor sufficient for a
  valid visual trace, and traces may span steps. *Role/link:* motivates semantic
  and temporal evidence selection.
- **P036 (269–273)** — Trace correctness and label correctness are independent.
  *Role/link:* justifies reporting evidence metrics separately from accuracy.

### 2.3 GUI Testing and Screenshot-Based Verification

- **P037 (277–285)** — Conventional GUI automation is strong under control but
  brittle under real-interface variability. *Role/link:* motivates fixed visual
  observations as an alternative evidence source.
- **P038 (287–291)** — The thesis begins after execution and treats screenshots
  as immutable observations that omit DOM state, backend effects, and other
  paths. *Role/link:* defines the evidential asymmetry developed in P039.
- **P039 (293–297)** — UI proxies establish visible messages or states, not
  delivery, persistence, or global completeness. *Role/link:* turns screenshot
  omissions into explicit claim boundaries.
- **P040 (299–303)** — Kretzer et al. connect stories to prototypes; this thesis
  adds executed order, four labels, and multi-state evidence. *Role/link:* states
  the difference from the closest prototype-oriented work.
- **P041 (305–312)** — GUISpector explores an application; this thesis fixes the
  trajectory and adds explicit abstention. *Role/link:* isolates evidence
  selection and incomplete-record decisions from exploration quality.
- **P042 (314–319)** — Cross-modal bug-fix verification supports treating this as
  software engineering rather than generic VQA. *Role/link:* broadens the
  verification context before UI-agent work.

### 2.4 Multimodal UI Agents and Trajectory Datasets

- **P043 (323–328)** — UI agents and verifiers both ground language in interfaces
  but optimize different outputs. *Role/link:* separates action selection from
  evidence-backed verification.
- **P044 (330–337)** — Mind2Web trajectories are reused as observations and
  augmented with reviewed requirements and labels. *Role/link:* explains the main
  dataset transformation.
- **P045 (339–344)** — Android in the Wild shows the setting could extend to
  mobile, but the thesis remains web-based. *Role/link:* introduces an external-
  validity boundary.
- **P046 (346–350)** — Absence from one trajectory does not establish global
  absence. *Role/link:* prepares the negative-versus-abstain policy in Chapter 3.

### 2.5 Visual Grounding and Evidence Localization

- **P047 (354–360)** — GUI grounding is a specialized language-to-region
  capability. *Role/link:* motivates explicit evaluation of evidence regions.
- **P048 (362–369)** — Set-of-Mark simplifies coordinate reference but depends on
  proposal coverage and may obscure the interface. *Role/link:* gives the design
  trade-off behind candidate marks.
- **P049 (371–376)** — The implemented OCR/UI candidate-mark method is evaluated
  for semantic evidence localization, not label improvement. *Role/link:* fixes
  the grounding contribution boundary.

### 2.6 Abstention and Decision-Making under Incomplete Evidence

- **P050 (380–385)** — Reject-option literature motivates withholding decisions,
  but the thesis does not learn a confidence threshold. *Role/link:* imports the
  abstention concept while limiting the methodological claim.
- **P051 (387–393)** — `ABSTAIN` is a semantic verdict distinct from coverage
  failure and visible contradiction. *Role/link:* operationalizes the concept for
  the thesis.
- **P052 (395–399)** — False fulfillment and abstention must be evaluated
  together because either can be gamed. *Role/link:* motivates the combined
  metric set.

### 2.7 Synthesis of the Research Gap

- **P053 (403–409)** — No reviewed line of work combines fixed ordered flows,
  requirement verdicts, evidence steps, optional regions, and preserved
  uncertainty. *Role/link:* states the integrated gap.
- **P054 (411–415)** — The missing contribution is a controlled separation of
  semantics, flow coverage, traces, and aggregation. *Role/link:* hands the
  argument to the formal design in Chapter 3.

## 3 Research Design and Problem Formulation

### 3.1 Research Strategy

- **P055 (430–437)** — Uses a design-and-evaluation strategy combining a formal
  contract, modular prototype, reviewed benchmark, controlled metrics, and
  qualitative diagnosis. *Role/link:* gives the overall methodological logic.
- **P056 (439–444)** — Defines one requirement/flow pair as the unit while
  acknowledging within-flow dependence and only 13 clusters. *Role/link:*
  motivates flow-level resampling and cautious intervals.
- **P057 (446–450)** — The evaluation is retrospective and cannot request new
  states. *Role/link:* trades evidence reproducibility for path-limited claims and
  enables separate retrieval diagnosis.

### 3.2 Formal Task Definition

- **P058 (454)** — Introduces the formal ordered-flow notation. *Role/link:* the
  following equation defines the screenshot sequence.
- **P059 (460–462)** — Defines each screenshot state, optional metadata, and the
  written requirement before introducing the verifier mapping. *Role/link:*
  formalizes the inputs.
- **P060 (468–470)** — Defines label, evidence, claim, uncertainty, and rationale
  outputs. *Role/link:* formalizes the multi-output contract.
- **P061 (477–480)** — Defines evidence units and makes order part of the input.
  *Role/link:* explains why identical images in another order can express another
  history.
- **P062 (482–485)** — The target is only what the recorded evidence supports,
  under a supplied evidence policy. *Role/link:* closes the formal definition
  with its epistemic boundary.

### 3.3 UI Evaluability

- **P063 (489–491)** — Introduces UI evaluability and its three-class definition
  list. *Role/link:* separates observability in principle from observed
  fulfillment.
- **P064 (501–507)** — Evaluability is relative to the modality, not coverage in
  one flow. *Role/link:* distinguishes a missing state from an inherently hidden
  requirement.
- **P065 (509–512)** — Separate evaluability labels preserve the visible/hidden
  boundary and enable stratified evaluation. *Role/link:* connects the construct
  to Chapter 6.

### 3.4 Verification Label Semantics

- **P066 (516–522)** — `FULFILLED` requires evidence for all material observable
  obligations while allowing specific visible proxies for routine dependencies.
  *Role/link:* defines the strongest verdict.
- **P067 (524–528)** — `PARTIALLY_FULFILLED` combines supported and unresolved
  material obligations. *Role/link:* gives a structured middle verdict for
  compound requirements.
- **P068 (530–533)** — `NOT_FULFILLED` requires visible counter-evidence rather
  than omission. *Role/link:* encodes the open-world asymmetry.
- **P069 (535–539)** — `ABSTAIN` represents insufficient or unsuitable evidence,
  not a missing prediction. *Role/link:* completes the four-label contract.

### 3.5 Claims and Deterministic Aggregation

- **P070 (543–548)** — Decomposition may split compound requirements, but claim
  text must be derived before evidence inspection. *Role/link:* prevents evidence
  leakage into the semantic contract.
- **P071 (550–554)** — Defines claim statuses, claim importance, and deterministic
  requirement aggregation. *Role/link:* introduces the rule block that follows.
- **P072 (563–566)** — Aggregation standardizes labels but cannot repair semantic
  claim errors; a counterfactual tests forced negative decisions. *Role/link:*
  bounds what deterministic policy can accomplish.

### 3.6 Evidence Contract

- **P073 (570–573)** — Separates screenshot-step traces from within-screen
  regions. *Role/link:* introduces the two evidence questions and their separate
  evaluations.
- **P074 (578–583)** — Step metrics assess ranking, while region metrics assess
  geometry, relevance, and sufficiency. *Role/link:* explains why IoU alone is
  inadequate.
- **P075 (585–591)** — Some evidence needs multiple regions, whole screens,
  transitions, or no region. *Role/link:* motivates the four region-applicability
  categories and localization abstention.

### 3.7 Operationalization of the Research Questions

- **P076 (595–599)** — RQ1 uses complete 258-item runs and multiple label,
  agreement, cost, and stability metrics. *Role/link:* operationalizes end-to-end
  performance.
- **P077 (601–605)** — RQ2 uses the controlled raw/gated by all/top-4 matrix with
  fixed remaining factors. *Role/link:* isolates decomposition and screenshot
  selection; grounding stays outside accuracy.
- **P078 (607–612)** — RQ3 uses a predefined descriptive taxonomy and optional
  stratification. *Role/link:* explicitly limits causal interpretation.

### 3.8 Scope and Non-Claims

- **P079 (616–621)** — Visible content, navigation, short transitions, validation,
  and results are in scope; hidden guarantees are not unless visibly framed.
  *Role/link:* defines the task boundary.
- **P080 (623–626)** — The study is neither formal verification nor exhaustive
  testing and generalizes only cautiously from 13 flows. *Role/link:* closes the
  design chapter with explicit non-claims.

## 4 Verification Approach and Implementation

### 4.1 Architecture

- **P081 (632)** — Introduces the modular pipeline diagram. *Role/link:* the
  following equation lists the processing stages.
- **P082 (644–649)** — Typed records preserve inputs, outputs, evidence, metadata,
  and replaceable components. *Role/link:* supports controlled component
  comparison and reproducibility.
- **P083 (651–654)** — The stages expose decomposition, retrieval, interpretation,
  and aggregation failures. *Role/link:* restates diagnosis—not assumed
  accuracy—as the architecture’s purpose.

### 4.2 Flow Ingestion and Screen Representation

- **P084 (658–662)** — Ingestion preserves identifiers, order, image dimensions,
  and original assets. *Role/link:* establishes stable evidence references.
- **P085 (664–668)** — Lightweight text assists retrieval, but screenshots remain
  authoritative. *Role/link:* prevents lexical matches from becoming verdict
  evidence.
- **P086 (670–674)** — Source flow material is kept outside versioned annotations
  and must be obtained separately. *Role/link:* connects implementation layout to
  licensing constraints.

### 4.3 Requirement Understanding

- **P087 (678–683)** — Requirement understanding optionally predicts evaluability
  and decomposes claims; predictions never replace gold during evaluation.
  *Role/link:* introduces the two semantic preprocessing operations.
- **P088 (685–691)** — Raw keeps one unit; gated decomposition splits 31 of 258
  requirements without LLM fallback. *Role/link:* defines the actual controlled
  RQ2 intervention.
- **P089 (693–696)** — The 541 reviewed claims support an oracle condition but not
  an automatic-decomposition claim. *Role/link:* separates diagnostic upper-bound
  analysis from the evaluated pipeline.

### 4.4 Screenshot Selection

- **P090 (700–704)** — Lexical retrieval is the deterministic primary selector;
  alternatives exist but are excluded from the matrix. *Role/link:* fixes the
  screenshot-selection factor.
- **P091 (706–710)** — Top-4 limits evidence per item, while batching may attach
  more than four unique images per API call. *Role/link:* prevents a misleading
  interpretation of cost and context.
- **P092 (712–717)** — Whole-flow avoids omission but adds context and image input;
  late-state misses motivate the comparison. *Role/link:* states the retrieval
  trade-off tested by RQ2.
- **P093 (719–728)** — The chronology ablation permutes images, remaps IDs, and
  tells the model order is unavailable. *Role/link:* tests the value of trusted
  order without presenting a false order.

### 4.5 Multimodal Claim Verification

- **P094 (732–738)** — Defines verifier inputs, structured outputs, validation,
  and the separation between malformed output and abstention. *Role/link:* gives
  the inference contract.
- **P095 (740–747)** — Specifies the primary Gemini model, comparison models,
  generation settings, provider controls, and archived metadata. *Role/link:*
  establishes reproducible model conditions.
- **P096 (749–758)** — Justifies each model choice and explains why the local
  SmolVLM2 pilot was not promoted. *Role/link:* frames the comparison as matched
  sensitivity rather than frontier coverage.
- **P097 (760–763)** — Keeps the historical Pro preview outside the controlled
  matrix. *Role/link:* prevents incomparable strong-model evidence from
  contaminating RQ2.
- **P098 (765–768)** — Repeats Gemini and Qwen runs because temperature zero is
  not determinism. *Role/link:* prepares the stability analysis.

### 4.6 Label Aggregation

- **P099 (772–777)** — Deterministic aggregation enforces evidence, contradiction,
  and hidden-property gates. *Role/link:* implements the central safety policy.
- **P100 (779–782)** — Aggregation reduces final-label prompt variance but cannot
  repair bad semantic statuses. *Role/link:* limits the claimed benefit of rules.
- **P101 (784–788)** — Forced-decision analysis maps frozen abstentions to
  negatives as a closed-world policy test. *Role/link:* isolates aggregation
  policy from new inference.

### 4.7 Region-Level Evidence Grounding

- **P102 (792–796)** — Early free-coordinate grounding was unstable and only
  partly helped by OCR. *Role/link:* motivates candidate-constrained grounding.
- **P103 (798–804)** — Candidate marks combine OCR/UI proposals with model
  selection and deterministic coordinate mapping. *Role/link:* separates
  proposal-coverage and selection errors.
- **P104 (806–810)** — Region output supports zero, one, or multiple boxes with
  complete coordinate provenance. *Role/link:* makes grounding reviewable across
  resolutions.
- **P105 (812–815)** — Bounding boxes are evaluated for validity, relevance, and
  sufficiency, not label accuracy. *Role/link:* fixes the contribution claim.

### 4.8 Annotation and Review Workbench

- **P106 (819–823)** — The workbench supports flow, requirement, evidence, and
  region review while storing review separately from predictions. *Role/link:*
  protects benchmark records from silent mutation.
- **P107 (825–832)** — UI-evaluability and region audits show different evidence
  and collect different judgments. *Role/link:* documents the targeted diagnostic
  workflows.
- **P108 (834–838)** — Both audits are single-author, targeted analyses separate
  from prediction-independent gold creation. *Role/link:* limits how their
  outcomes can be interpreted.

### 4.9 Reproducibility and Artifact Management

- **P109 (842–847)** — Configurations and preflight manifests freeze model,
  benchmark, environment, hashes, commands, and cost guards. *Role/link:* defines
  experiment preparation.
- **P110 (849–853)** — Runs archive outputs and usage, metrics are regenerated
  from matching manifests, and the public package is aggregate-only. *Role/link:*
  defines result provenance and redistribution scope.
- **P111 (855–858)** — Automated tests cover implementation consistency but not
  semantic validity. *Role/link:* prevents software-test success from becoming an
  empirical claim.

### 4.10 Implementation Boundaries

- **P112 (862–868)** — Retrieval, OCR, hosted-model reproducibility, and local
  hardware impose prototype limits. *Role/link:* records implementation threats
  before the dataset chapter.
- **P113 (870–874)** — Uploaded-flow functionality exceeds what the fixed
  benchmark and incomplete grounding review validate. *Role/link:* separates
  product features from scientific contributions.

## 5 Dataset and Annotation Methodology

### 5.1 Main Flow Dataset

- **P114 (880)** — Defines the 13 Mind2Web-derived web flows as observations for
  separately represented UI requirements. *Role/link:* establishes the primary
  dataset and excludes action prediction.
- **P115 (882–888)** — Describes application domains and the multi-state
  structures available in cart and search flows. *Role/link:* shows why sequences
  can support more than isolated screenshots.
- **P116 (890–893)** — Reports 258 items, 173 source requirements, 85
  contrastives, 541 claims, and prediction-independent review. *Role/link:*
  establishes benchmark scale and provenance.
- **P117 (895)** — Shows the fulfilled-heavy label distribution and explains why
  accuracy is insufficient. *Role/link:* motivates macro-F1 and per-class
  reporting.
- **P118 (897–903)** — Reports the separate evaluability distribution and
  distinguishes modality suitability from flow coverage. *Role/link:* prepares
  the auxiliary evaluability analysis.

### 5.2 From Candidates to Verification Gold

- **P119 (907–909)** — Requirements originate from UI flows, so staged artifacts
  and human review separate generation from gold annotation. *Role/link:*
  discloses the reversed construction direction.
- **P120 (911–915)** — Harvesting creates noisy hypotheses; filtering and review
  decide which become candidates or source requirements. *Role/link:* prevents
  candidate status from implying correctness.
- **P121 (917)** — Separates candidate/source counts and lists the extra
  verification annotations added at gold stage. *Role/link:* distinguishes
  requirement acceptance from verification labeling.
- **P122 (919)** — Contrastive requirements add completeness, hidden,
  comparative, and absent-control cases, subject to review. *Role/link:* explains
  how non-positive cases enter the benchmark.
- **P123 (921–928)** — Source evidence dependence and contrastive hard-case bias
  remain despite prediction-independent review. *Role/link:* states construction
  threats and the controls used in reporting and resampling.

### 5.3 Annotation Schema

- **P124 (932)** — Introduces the four requirement-label definition list.
  *Role/link:* translates Chapter 3 semantics into annotation instructions.
- **P125 (939)** — Defines claim statuses, importance, evidence links, and the
  claim-matching problem. *Role/link:* connects annotation detail to later claim
  metrics.
- **P126 (941–947)** — Makes screenshot steps the stable primary evidence unit
  and separates region localization. *Role/link:* aligns annotation with the two
  evidence evaluations.

### 5.4 Running Example: Public Access to Amtrak Dining Information

- **P127 (951)** — Introduces a clean positive requirement quotation.
  *Role/link:* opens the concrete walkthrough.
- **P128 (955–960)** — Decomposes the requirement and links public navigation and
  no-sign-in claims to steps 1, 4, and 5. *Role/link:* demonstrates a fulfilled
  multi-step trace.
- **P129 (962–966)** — Stronger applicability or ownership wording would exceed
  the same evidence and change the label. *Role/link:* demonstrates that wording,
  not UI plausibility, controls the verdict.

### 5.5 PURE as Exploratory External Material

- **P130 (970)** — PURE supplies independently sourced, longer, context-dependent
  requirements unlike flow-derived items. *Role/link:* introduces external
  provenance diversity.
- **P131 (972–977)** — Describes extraction, accepted Split/Merge and Mashboot
  counts, independent review, and stored provenance. *Role/link:* documents PURE
  construction.
- **P132 (979–982)** — Restricts PURE to qualitative document-to-UI consistency,
  not executed implementation conformance. *Role/link:* prevents mixing the two
  evidence regimes.

### 5.6 Review Workflow and Quality Controls

- **P133 (986–990)** — Candidate review checks requirement quality; verification
  review checks evaluability, labels, claims, evidence, uncertainty, and
  rationale. *Role/link:* distinguishes the two review stages.
- **P134 (992–997)** — Structural validation catches internally inconsistent
  labels but cannot prove the reviewer’s interpretation. *Role/link:* separates
  schema quality from semantic gold quality.
- **P135 (999–1004)** — All accepted items received primary-author review
  independent of evaluated predictions. *Role/link:* defines the reference
  standard and its provenance.
- **P136 (1006–1009)** — Evaluability and region reviews use separate targeted
  samples because agreement does not transfer across outputs. *Role/link:* keeps
  auxiliary audits distinct.

### 5.7 Benchmark Characteristics

- **P137 (1013–1017)** — Items are clustered by flow and preserve identifiers for
  flow-level diagnosis and resampling. *Role/link:* justifies the statistical
  unit.
- **P138 (1019–1024)** — Claim counts vary because requirements range from atomic
  to multi-obligation and visible/hidden combinations. *Role/link:* motivates
  decomposition while warning about matching difficulty.
- **P139 (1026–1030)** — Reference evidence may span steps and may not enumerate
  every valid alternative. *Role/link:* limits automatic evidence-overlap
  interpretation.
- **P140 (1032–1036)** — Manifests freeze counts and gold hashes so missing
  predictions are not misread as abstentions. *Role/link:* prevents historical
  denominator errors.

### 5.8 Data Governance

- **P141 (1040–1044)** — Mind2Web test artifacts stay local and are reconstructed
  only after official acquisition. *Role/link:* defines the main dataset’s
  redistribution boundary.
- **P142 (1046–1051)** — PURE source documents and substantial content are
  excluded because of uncertain underlying rights. *Role/link:* hands detailed
  reproducibility implications to Section 7.7.

## 6 Evaluation

### 6.1 Compared Systems

- **P143 (1057–1063)** — Defines the 258-item Gemini 3.1 Flash-Lite 2x2 matrix and
  holds all factors except claim and screenshot policy constant. *Role/link:*
  establishes the primary RQ2 comparison.
- **P144 (1065–1070)** — Adds matched Gemini 2.5, hosted Qwen, deterministic
  baselines, and carefully separated historical/oracle runs. *Role/link:*
  establishes RQ1 sensitivity without contaminating the matrix.
- **P145 (1072–1076)** — Requires complete coverage and archives exact execution
  metadata. *Role/link:* defines headline-run admissibility.
- **P146 (1078–1082)** — Retains the earlier 201-item comparison only as
  internally valid development history. *Role/link:* prevents it from replacing
  the full benchmark in final answers.

### 6.2 Label Metrics

- **P147 (1086)** — Defines accuracy and shows a fulfilled-only baseline already
  reaches 66.7%. *Role/link:* demonstrates class-imbalance risk.
- **P148 (1088)** — Defines macro-F1 and explains its sensitivity to minority
  classes. *Role/link:* supplies the main balanced label metric.
- **P149 (1090)** — Defines false fulfillment as the error rate among strongest
  positive claims and notes its gaming risk. *Role/link:* supplies the
  safety-oriented metric.
- **P150 (1092)** — Defines abstain rate and prediction coverage and keeps missing
  outputs separate. *Role/link:* completes label-level reporting.

### 6.3 Evidence Metrics

- **P151 (1096)** — Defines hit@k, recall@k, precision@k, and MRR over reviewed
  screenshot steps. *Role/link:* establishes automatic trace metrics.
- **P152 (1098)** — Explains that one retrieved step may not complete a multi-step
  trace and overlap does not test interpretation. *Role/link:* bounds what the
  metrics mean.
- **P153 (1100)** — Warns that 201-item and 258-item evidence artifacts are not
  interchangeable. *Role/link:* enforces run-specific evidence reporting.

### 6.4 Claim Metrics and Qualitative Analysis

- **P154 (1104)** — Claim matching precedes status scoring, and decomposition
  wording/granularity can distort automatic metrics. *Role/link:* motivates
  manual claim inspection.
- **P155 (1106)** — Defines major error categories and semantic pattern tags.
  *Role/link:* introduces the qualitative RQ3 analysis.

### 6.5 Statistical Comparison and Run Stability

- **P156 (1110–1117)** — Uses paired bootstrap resampling of complete flows to
  preserve within-flow dependence. *Role/link:* defines uncertainty intervals.
- **P157 (1119–1123)** — Only 13 clusters limit precision, so intervals and
  per-flow results remain descriptive. *Role/link:* prevents population-level
  overclaiming.
- **P158 (1125–1130)** — Independent repetitions test operational stability
  without increasing the sample denominator. *Role/link:* defines agreement and
  metric-range reporting.
- **P159 (1132–1138)** — Chronology effects are reported for the full benchmark
  and several diagnostic subsets, including a single-screen control. *Role/link:*
  establishes the order-ablation subgroup design and its limits.

### 6.6 UI-Evaluability Evaluation

- **P160 (1142–1146)** — Compares joint model evaluability predictions with the
  reviewed three-class labels using imbalance-aware metrics. *Role/link:*
  operationalizes the first auxiliary analysis.
- **P161 (1148–1150)** — A deterministic lexical classifier tests whether cheap
  rules can recover the visible/hidden boundary. *Role/link:* provides a simple
  baseline.
- **P162 (1152–1159)** — A targeted 81-disagreement author audit records boundary
  resolutions without treating PURE designs as executed trajectories.
  *Role/link:* defines the diagnostic audit and amendment protocol.
- **P163 (1161–1166)** — Stratifies verification behavior by evaluability but
  treats the four non-verifiable items cautiously. *Role/link:* connects
  evaluability to fulfillment errors.

### 6.7 Region-Level Evidence Evaluation

- **P164 (1175–1182)** — Defines a claim/screenshot/region audit with applicability,
  validity, relevance, and sufficiency judgments. *Role/link:* operationalizes
  grounding independently of label accuracy.
- **P165 (1184)** — Introduces the region-analysis output list. *Role/link:* the
  following list specifies completion, proposal, validity, relevance,
  sufficiency, and abstention measures.
- **P166 (1196–1202)** — Defines the deterministic 60-item V7 sample and excludes
  incompatible earlier methods from pooled accuracy. *Role/link:* fixes grounding
  sample provenance.

### 6.8 Error-Analysis Protocol

- **P167 (1211–1215)** — Codes every incorrect and unsafe-positive prediction
  using a frozen taxonomy while separating abstentions. *Role/link:* defines RQ3
  units and prevents unlike errors from being merged.
- **P168 (1217–1223)** — Lists model, evidence, and requirement-pattern
  categories and flags reference disagreements. *Role/link:* specifies the coding
  scheme.
- **P169 (1225–1228)** — Requires explicit denominators and only a small set of
  examples alongside counts. *Role/link:* prevents anecdotal error claims.

### 6.9 Development-Stage Label Performance on Flows 01–10

- **P170 (1232)** — Introduces the controlled 201-item preliminary table.
  *Role/link:* opens development-history results.
- **P171 (1234)** — Provides the preliminary label-table caption. *Role/link:*
  identifies the artifact interpreted by P172–P175.
- **P172 (1243)** — Pro leads preliminary label metrics but costs about 61 times
  Flash Lite under provisional pricing. *Role/link:* shows a performance/cost
  trade-off outside the final matrix.
- **P173 (1245–1250)** — Whole-flow Flash Lite beats batched top-k, whose cited
  evidence is often interpreted too broadly. *Role/link:* provides early evidence
  against an assumed evidence-first accuracy advantage.
- **P174 (1252)** — The deterministic baseline combines heavy abstention with
  unsafe positives. *Role/link:* shows conservative aggregation cannot compensate
  for weak semantic statuses.
- **P175 (1254)** — Minority classes explain low macro-F1 and require confusion
  matrices and per-class metrics. *Role/link:* states a final-report requirement;
  wording still reads as a drafting instruction.

### 6.10 Development-Stage Evidence Retrieval

- **P176 (1258)** — Introduces preliminary step-evidence results for two
  comparable configurations. *Role/link:* opens development evidence analysis.
- **P177 (1260)** — Provides the preliminary evidence-table caption. *Role/link:*
  identifies the artifact interpreted by P178–P179.
- **P178 (1267–1271)** — Top-k often finds one relevant step but misses much of
  multi-step gold evidence. *Role/link:* separates hit success from complete
  trace recall.
- **P179 (1273–1275)** — Weaker top-k labels show that reduced irrelevant context
  can still omit decisive evidence. *Role/link:* connects retrieval metrics to
  label consequences.

### 6.11 Dominant Error Patterns

- **P180 (1279)** — Historical and current runs share recurring mechanisms, but
  their counts cannot be pooled. *Role/link:* licenses qualitative continuity
  while protecting denominator validity.
- **P181 (1281–1285)** — Models over-fulfill when a visible entry point becomes
  proof of outcomes or universal behavior. *Role/link:* identifies the direct
  mechanism behind false fulfillment.
- **P182 (1287–1290)** — Models infer hidden persistence, delivery, payment,
  security, and backend outcomes from UI proxies. *Role/link:* identifies
  visible/hidden boundary failures.
- **P183 (1292–1296)** — Universal and comparative wording requires broader
  evidence than one observed instance. *Role/link:* identifies scope
  generalization errors.
- **P184 (1298–1300)** — Lexical selection misses late cart, checkout, result,
  review, and summary states. *Role/link:* identifies a retrieval-specific
  failure pattern.
- **P185 (1302–1307)** — Most label-boundary disputes concern partial versus
  abstain and negative versus abstain. *Role/link:* ties disagreement to the
  contradiction requirement and annotation guidance.

### 6.12 Late-State Failure Example

- **P186 (1311)** — The Six Flags flow concentrates requirements whose decisive
  evidence occurs in steps 8–10. *Role/link:* introduces a representative lexical
  retrieval failure.
- **P187 (1313–1317)** — Without the final cart screen, totals and modification
  controls cannot be cited; late priors and fallback can repair retrieval.
  *Role/link:* traces the failure to evidence omission rather than interpretation.
- **P188 (1319–1322)** — Complete flows also cost more and contain irrelevant
  content. *Role/link:* restores the multi-objective trade-off behind RQ2.

### 6.13 Current Controlled Full-Benchmark Comparison

- **P189 (1326)** — Defines the completed 258-item 2x2 matrix with only claim and
  screenshot policy varied and full coverage. *Role/link:* opens the primary
  final experiment.
- **P190 (1335–1341)** — Raw top-4 significantly reduces accuracy, macro-F1, and
  MRR while saving almost no cost. *Role/link:* answers the screenshot-selection
  part of RQ2.
- **P191 (1343)** — Gated decomposition has no consistent all-flow benefit,
  increases false fulfillment there, but improves top-4 macro-F1. *Role/link:*
  answers the decomposition part as an interaction rather than a universal gain.
- **P192 (1345)** — Forcing abstentions to negative labels reduces accuracy and
  macro-F1 without affecting false fulfillment. *Role/link:* demonstrates that
  missing evidence and contradiction should remain distinct.

### 6.14 Run-to-Run Stability

- **P193 (1349–1354)** — Describes three executions of the two Gemini anchors and
  Qwen baseline with complete, failure-free calls. *Role/link:* establishes the
  repetition evidence.
- **P194 (1356–1360)** — Gemini labels are identical across runs, while evidence
  MRR varies slightly. *Role/link:* shows label stability does not imply trace
  invariance.
- **P195 (1362–1367)** — Qwen has small metric and label variation but high
  agreement. *Role/link:* shows strong descriptive stability without claiming
  determinism.
- **P196 (1369–1372)** — Reports repetition cost and keeps unvalidated/free-form
  regions outside the mature contribution. *Role/link:* closes operational
  stability accounting.
- **P197 (1374)** — Gemini 3.1 outperforms Gemini 2.5 and the models agree on
  83.3% of labels. *Role/link:* supplies matched model sensitivity for RQ1.
- **P198 (1376–1384)** — Qwen and Gemini tie on accuracy/MRR but differ strongly
  in macro-F1 and false fulfillment, with hosted-stack opacity noted.
  *Role/link:* demonstrates why headline accuracy is insufficient.
- **P199 (1386)** — Introduces the order-unavailable robustness subsection.
  *Role/link:* separates chronology results within stability analysis.
- **P200 (1388–1395)** — Removing trusted order lowers accuracy, macro-F1, and MRR
  while increasing abstention. *Role/link:* reports the aggregate chronology
  effect.
- **P201 (1397–1404)** — Bootstrap differences and 28 label flips show aggregate
  harm but no uniformly safer direction. *Role/link:* limits interpretation of
  the order effect.
- **P202 (1406–1414)** — Sequence-sensitive items flip more often than the
  single-screen control, but subgroup uncertainty remains. *Role/link:* supports
  operational relevance of order without claiming category-specific causality.

### 6.15 Preliminary UI-Evaluability Results

- **P203 (1418–1424)** — Model evaluability agreement is 79.5% but macro-F1 and
  minority recall are weak. *Role/link:* reports the main auxiliary result and
  exposes class imbalance.
- **P204 (1426–1432)** — The model treats a visible core as if the entire
  requirement were UI-verifiable. *Role/link:* links evaluability mistakes to
  over-fulfillment and partial/abstain instability.
- **P205 (1434–1439)** — The deterministic classifier mostly predicts the
  majority class despite 72.7% accuracy. *Role/link:* shows lexical rules are
  inadequate for the construct.
- **P206 (1441–1446)** — Results remain preliminary until the disagreement audit
  is resolved and PURE is separated. *Role/link:* blocks premature final claims
  and biased recomputation.

### 6.16 Preliminary Region-Grounding Findings

- **P207 (1452–1457)** — All-flow runs demonstrate implemented region output and
  explicit no-region abstention. *Role/link:* establishes implementation
  coverage, not quality.
- **P208 (1459–1465)** — Early lexical/free-coordinate boxes were mostly wrong,
  and resolution alone did not fix semantics. *Role/link:* shows why generated
  region count is not a localization metric.
- **P209 (1467–1473)** — Candidate-mark pilots look better, but the reviewed
  subset is too small and incompatible methods are not pooled. *Role/link:*
  reports promising development evidence without benchmark-wide estimation.
- **P210 (1475–1478)** — The pipeline produces regions, but final relevance,
  sufficiency, coverage, and abstention claims await the frozen review.
  *Role/link:* closes Chapter 6 with the remaining grounding boundary.

## 7 Discussion and Threats to Validity

### 7.1 Interpretation and Practical Implications

- **P211 (1486–1492)** — Staging does not consistently improve labels; top-4
  loses evidence and gated decomposition only helps macro-F1 under restriction.
  *Role/link:* synthesizes the main RQ2 result.
- **P212 (1494–1499)** — Evidence-first primarily improves inspectability by
  separating retrieval, visual reasoning, and policy errors. *Role/link:* states
  the demonstrated contribution despite mixed accuracy.
- **P213 (1501–1507)** — Practical deployment should use complete short flows and
  adaptive retrieval for longer ones. *Role/link:* translates observed late-state
  failures into a design recommendation.
- **P214 (1509–1515)** — Fulfillment thresholds depend on risk context, while this
  thesis fixes one policy across applications. *Role/link:* separates the
  evaluated construct from alternative deployment policies.

### 7.2 Internal Validity

- **P215 (1519–1524)** — Gold labels, claims, evidence, and evaluability received
  prediction-independent primary-author review; a later audit is diagnostic.
  *Role/link:* states the reference-standard control.
- **P216 (1526–1531)** — Requirements and screenshots share flow provenance, but
  contrastive separation, resampling, and PURE reporting expose dependencies.
  *Role/link:* acknowledges construction dependence before construct and external
  validity.
- **P217 (1533)** — Models and historical reports depend on prompts, versions,
  image preparation, retries, aggregation, and matching manifests. *Role/link:*
  motivates strict final-run provenance.

### 7.3 Construct Validity

- **P218 (1537)** — The four labels are a deliberate conservative construct, not
  the only possible verification semantics. *Role/link:* opens the construct-
  validity argument.
- **P219 (1539–1549)** — Label meanings do not fully specify evidence sufficiency,
  leaving some decisions to model priors; detailed criteria were avoided on the
  narrow benchmark. *Role/link:* identifies the central calibration trade-off and
  prepares future rubric work.
- **P220 (1551)** — Evidence-step overlap may miss valid alternatives or reward a
  step interpreted incorrectly. *Role/link:* limits automatic trace metrics.
- **P221 (1553–1557)** — Useful grounding may require whole states, multiple
  regions, or transitions, so geometry alone is insufficient. *Role/link:*
  justifies human relevance and sufficiency judgments.
- **P222 (1559–1563)** — UI evaluability has the same risk-dependent proxy/hidden
  boundary as fulfillment. *Role/link:* extends the evidence-sufficiency problem
  to the auxiliary construct.
- **P223 (1565)** — Claim metrics confound decomposition, text matching, and
  status prediction. *Role/link:* requires claim-match recall and matched-status
  quality to remain separate; wording still reads as a drafting instruction.

### 7.4 External Validity

- **P224 (1569)** — Thirteen web flows do not establish generalization to other
  interfaces, requirements, or unvisited states. *Role/link:* states the sample
  and modality limitation.
- **P225 (1571–1581)** — Source requirements were reconstructed from established
  flows, no UIs or defects were generated, and contrastives are constructed
  deviations. *Role/link:* limits results to evidence interpretation rather than
  requirements-first defect detection.
- **P226 (1583–1585)** — PURE adds independent requirements documents but only
  supports document-to-UI consistency. *Role/link:* shows partial provenance
  broadening without claiming executed conformance.

### 7.5 Reliability and Reproducibility

- **P227 (1589)** — Hosted APIs, caching, versions, failures, and usage metadata
  threaten reproducibility and must be reported. *Role/link:* states operational
  reliability requirements.
- **P228 (1591)** — A 201-versus-258 denominator mismatch once produced a false
  31.8% metric instead of 75.1%. *Role/link:* demonstrates why frozen matching
  manifests are necessary.

### 7.6 Current Scope Limitations

- **P229 (1595–1603)** — Step evidence is mature, region review remains separate,
  screenshots cannot prove hidden truth, and the 2x2 matrix tests only one model.
  *Role/link:* collects the final empirical non-claims.

### 7.7 Dataset Licensing and Artifact Availability

- **P230 (1607–1616)** — Mind2Web licensing and repository guidance restrict the
  public artifact to code, configurations, citations, and aggregate results.
  *Role/link:* explains controlled access to identifiers, annotations, and raw
  interactions.
- **P231 (1618–1626)** — Uncertain third-party rights similarly exclude PURE
  documents, figures, text, and reproducing outputs. *Role/link:* defines the
  conservative PURE release boundary.

## 8 Conclusion

### 8.1 Summary

- **P232 (1632–1635)** — Restates evidence-bounded verification of written UI
  requirements against ordered screenshots with preserved uncertainty.
  *Role/link:* reintroduces the task at conclusion level.
- **P233 (1637–1644)** — Summarizes the contract, pipeline, 258-item benchmark,
  compared factors, metrics, and region extension. *Role/link:* inventories the
  work before answering the RQs.

### 8.2 Answers to the Research Questions

- **P234 (1648–1660)** — RQ1 answer: models are useful but incomplete; model
  choice and order affect outcomes, and accuracy alone is insufficient.
  *Role/link:* combines matched model and chronology findings.
- **P235 (1662–1670)** — RQ2 answer: decomposition effects depend on screenshot
  restriction, while lexical top-4 harms accuracy/MRR for negligible savings.
  *Role/link:* gives the conditional architecture conclusion and keeps regions
  outside accuracy.
- **P236 (1672–1679)** — RQ3 answer: errors involve unsupported outcomes, hidden
  proxies, quantifiers, and late states; forced negatives harm accuracy.
  *Role/link:* synthesizes recurring mechanisms and preserves the abstain/negative
  distinction.

### 8.3 Contributions

- **P237 (1686–1690)** — Claims the evidence-bounded formulation and modular
  implementation across all pipeline stages. *Role/link:* states the conceptual
  and engineering contribution.
- **P238 (1692–1699)** — Claims the reviewed benchmark, interaction finding, and
  multi-outcome evaluation framework. *Role/link:* states the empirical and
  methodological contribution.

### 8.4 Future Work

- **P239 (1703–1709)** — Proposes a layered evidence-sufficiency rubric with
  general principles and domain profiles. *Role/link:* addresses model-dependent
  interpretation without replacing semantic intelligence.
- **P240 (1711–1718)** — Proposes a larger requirements-first benchmark with
  independent requirements, multiple UI/implementation variants, deviations,
  held-out applications, more flows, and reviewers. *Role/link:* addresses the
  reversed construction direction and supports rubric evaluation.
- **P241 (1720–1725)** — Proposes adaptive evidence acquisition, validated
  semantic retrieval, and improved multi-region/transition grounding.
  *Role/link:* closes with implementation-oriented extensions.

## End-to-End Argument in One Page

1. Coding-agent capability increases the need for efficient verification, but
   UI requirements and visible evidence use different modalities.
2. A fixed screenshot sequence is useful, reproducible evidence but is incomplete
   and cannot prove hidden or global properties.
3. The thesis therefore defines four evidence-bounded fulfillment verdicts,
   separates UI evaluability, and requires traceable screenshot evidence.
4. The implementation tests whether decomposition and screenshot selection help
   a multimodal verifier rather than assuming they do.
5. A reviewed 258-item benchmark enables controlled comparison, but its
   requirements were reconstructed from observed flows and its items are
   clustered across only 13 applications.
6. Whole-flow raw verification performs best in the primary matrix. Lexical
   top-4 loses decisive evidence for negligible savings; decomposition only helps
   macro-F1 under restricted evidence and can increase false fulfillment.
7. Models are stable within repeated runs but differ across model families,
   especially in minority classes and false fulfillment.
8. Errors concentrate around visible proxies for unobserved outcomes,
   quantifiers, hidden properties, and late states.
9. Evidence-first structure is most clearly valuable for diagnosis and
   traceability rather than uniform label-accuracy improvement.
10. Future work should make evidence sufficiency more explicit and test it on a
    larger, genuinely requirements-first benchmark with held-out applications.
