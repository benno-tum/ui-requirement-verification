# Automated UI Requirement Verification from Ordered Screenshot Sequences

## Full Working Draft

**Status:** Working thesis prose, updated 24 July 2026. Chapters 1–8 contain
continuous draft text for the parts supported by the current implementation and
frozen experiments. Final independent-review results for UI evaluability and
region-level grounding are deliberately not anticipated. Non-rendered comments
mark the locations at which those results can be inserted after review. The
quantitative source of truth remains
[`thesis_evidence_audit.md`](thesis_evidence_audit.md).

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

Screenshot-step evidence and region-level evidence are evaluated as two
different outputs. Screenshot-step retrieval is evaluated automatically against
the reviewed evidence steps. Region-level grounding is not treated as a cause of
better label accuracy; it is an additional traceability output whose relevance,
sufficiency, and coverage require human evaluation. The repository contains
candidate-mark grounding runs over all 13 flows and the review infrastructure
needed for this evaluation. PURE remains exploratory because acceptance status
does not remove its provenance and post-hoc-review limitations.

The thesis does not claim to establish industrial readiness or broad generalization from 13 flows. Its goal is to make the task and its failure modes measurable, to test several concrete verifier designs, and to identify what screenshots can and cannot support as requirement evidence.

The remainder of the thesis first establishes the conceptual and technical
foundations, formalizes the verification task, describes the implemented
pipeline, and then presents the benchmark, evaluation, results, limitations, and
conclusions.

## 2 Foundations and Related Work

### 2.1 Requirements as Verification Contracts

A software requirement states an obligation that an implementation is expected
to satisfy. Requirements may describe functionality, quality properties,
constraints, interactions, or externally visible outcomes. In practice, their
role is broader than that of natural-language documentation. They coordinate
expectations between stakeholders and provide the reference against which
design, implementation, and testing decisions are justified. Verification
therefore depends not only on the implemented system, but also on the precision
and observability of the requirement itself.

Natural-language requirements are attractive because stakeholders can read and
write them without committing to a formal notation. The same flexibility makes
them vulnerable to ambiguity. Berry, Kamsties, and Krieger (2003) describe
linguistic sources such as vague terms, implicit references, and underspecified
quantifiers. Gervasi et al. (2019) further emphasize that ambiguity is not one
uniform defect: it may arise from the wording, the surrounding domain context,
or different interpretations held by the involved actors. A verifier cannot
remove this ambiguity by inspecting the implementation. If a requirement asks
for “all relevant results” without defining relevance, even complete access to
the UI would not establish a unique expected outcome.

This thesis treats a requirement as the primary semantic contract and does not
silently strengthen or weaken it to match the available screenshots. Its
observable obligations are extracted before the evidence is interpreted. Terms
such as “all,” “only,” “always,” and “closest” are retained because they change
what would count as sufficient evidence. This discipline is important for
multimodal models, which can otherwise replace the literal contract with a
plausible story about what the interface probably does.

UI requirements occupy a useful but difficult subset of software requirements.
They may constrain visible content, available controls, navigation, validation
feedback, state changes, or the presentation of results. Some are directly
observable in a single state, while others become observable only through a
sequence. A requirement that a selected item appears in a cart needs at least a
selection state and a later cart state. A requirement that a menu is reachable
without authentication requires the navigation path and the absence of an
intervening sign-in wall. This temporal structure motivates the use of ordered
screenshot flows rather than isolated images.

### 2.2 Requirements Traceability

Traceability links requirements to the artifacts that refine, implement, or
verify them. Cleland-Huang et al. (2014) characterize software traceability as a
persistent challenge because projects contain heterogeneous artifacts, links
change as systems evolve, and manual maintenance is expensive. Classical links
may connect requirements to design elements, source code, test cases, defects,
or other requirements. The present task adds a visual trace target: a
requirement decision should be connected to the recorded UI states that support
or contradict it.

This link is not equivalent to a conventional document-retrieval result. A
screenshot can contain the same words as a requirement without demonstrating
the required behavior. Conversely, an icon, selected state, or layout change may
provide relevant evidence without repeating the requirement vocabulary. A
complete trace may also span several steps. The system must therefore preserve
both semantic relevance and temporal position.

The trace is valuable even when it does not improve classification accuracy. A
label without evidence forces a reviewer to repeat the entire inspection. A
label with a screenshot step and a localized region can be challenged at the
point where the model's interpretation entered the decision. For this reason,
the thesis evaluates label correctness and evidence traceability separately. A
correct label with an incorrect trace is not treated as a fully satisfactory
verification output, and a correct trace does not guarantee a correct label.

### 2.3 GUI Testing and Screenshot-Based Verification

GUI test automation normally executes interactions and checks explicit
assertions against a running system. It can provide strong evidence when the
environment, selectors, input data, and expected states are controlled. In
real-world systems, however, interfaces change, element locators become brittle,
external services introduce nondeterminism, and visually equivalent states may
have different internal representations. Nass, Alégroth, and Feldt (2021)
argue that several challenges of GUI test automation are inherent to the
complexity and variability of graphical interfaces rather than temporary
tooling deficiencies.

The task in this thesis does not replace executable GUI tests. It starts after a
flow has already been recorded and asks what that finite visual record supports
about a textual requirement. This narrower setting has practical advantages:
the original application does not need to remain available, interaction scripts
do not need to be replayed, and heterogeneous websites can be evaluated through
a shared screenshot representation. It also loses information. Screenshots do
not expose the DOM, backend state, network effects, or alternative paths that
were not recorded.

These limitations define the epistemic boundary of the task. A screenshot may
show a confirmation message, but it cannot establish that an email was
delivered. It may show a selected checkbox, but not that the preference remains
stored after a later session. It may show one result page, but not that the
result set is globally complete. Screenshot-based verification is therefore a
form of evidence-bounded conformance assessment, not proof of total system
correctness.

Kretzer et al. (2025) provide a close requirements-oriented comparison by
connecting user stories to GUI prototypes and studying whether a story is
represented in the prototype. The present work differs by using ordered
observations of an executed interface, an explicit four-label contract, and
evidence links that may span multiple states. Massenon, Gambo, and Khan (2026)
study cross-modal verification of mobile-app bug fixes and demonstrate the
broader relevance of combining textual engineering artifacts with visual
evidence. Their task concerns bug-fix consistency rather than requirement
fulfillment, but it motivates treating multimodal verification as a software
engineering problem rather than generic visual question answering.

### 2.4 Multimodal UI Agents and Trajectory Datasets

Multimodal UI agents receive visual and textual observations and select actions
in an interface. Their progress is relevant because both UI action selection and
UI verification require models to connect language with visible state. The
tasks nevertheless have different objectives. An agent can complete a task
without explaining which evidence establishes a requirement, and a verifier
does not need to choose or execute the next interaction.

Mind2Web contains open-ended web tasks, action sequences, and observations from
real websites (Deng et al., 2023). Its original purpose is to evaluate
generalist web agents across tasks, websites, and domains. This thesis reuses a
small set of its ordered trajectories as visual observations, not as an
action-prediction benchmark. The original task description and action sequence
provide context for reconstructing a flow, while the thesis benchmark adds
separately reviewed UI requirements, fulfillment labels, and evidence
annotations.

Android in the Wild provides a related trajectory dataset for mobile-device
control (Rawles et al., 2023). It illustrates that ordered visual interaction
data is not limited to the web. The current evaluation remains web-based because
the reviewed benchmark and implementation were developed around Mind2Web.
Generalization to native mobile interfaces is therefore a future validation
question rather than an empirical claim of this thesis.

The use of a recorded trajectory changes the meaning of absence. If an element
does not appear in the flow, the system may not have visited the state in which
it appears. The trajectory can support positive observations and visible
contradictions, but it cannot generally establish global non-existence. This
asymmetry is central to the label policy introduced in Chapter 3.

### 2.5 Visual Grounding and Evidence Localization

Visual grounding connects a linguistic expression to a spatial region. In UI
settings, the target may be a control, text block, icon, status indicator, or
compound arrangement. SeeClick trains and evaluates grounding capabilities
specialized for graphical user interfaces and shows the importance of
interface-specific localization (Cheng et al., 2024). UGround similarly treats
GUI grounding as a dedicated capability rather than assuming it emerges
reliably from a general-purpose vision-language model (Gou et al., 2025).

Set-of-Mark prompting overlays numbered candidate regions and asks a
multimodal model to refer to the marks instead of emitting unconstrained pixel
coordinates (Yang et al., 2023). The approach can simplify the mapping from
language to pixels, but its upper bound depends on the proposal generator: a
model cannot select a relevant region that was never proposed. Mark density and
placement may also obscure the interface. SeeAct reports that Set-of-Mark was
not its strongest strategy for web-agent grounding and benefited from combining
visual information with HTML-derived candidates (Zheng et al., 2024).

The implementation in this thesis uses a Set-of-Mark-inspired candidate-mark
variant. Its candidates originate from OCR and UI-region detection rather than
the exact segmentation procedure of the original method. It is therefore not
described as a replication of Set-of-Mark. Region grounding is evaluated as an
evidence-localization output. The thesis does not assume that returning a box
improves the requirement label, and it does not treat coordinate validity as
semantic correctness. A box must be relevant to the claim and sufficiently
specific to help a reviewer understand the decision.

### 2.6 Abstention and Decision-Making under Incomplete Evidence

Classification with a reject option permits a system to withhold a concrete
prediction when the expected cost of an error is too high or the available
information is insufficient. Hendrickx et al. (2024) survey reject-option
methods across machine learning, while Wen et al. (2025) discuss abstention in
large language models. The common intuition is applicable here, but the thesis
does not attempt to learn a calibrated confidence threshold.

`ABSTAIN` is instead a semantic label in the supplied verification contract. It
means that the screenshot flow does not justify a reliable positive or negative
decision. This differs from a missing API output, parsing failure, or skipped
item. Those are coverage failures and must be reported separately. It also
differs from `NOT_FULFILLED`: a negative label requires visible
counter-evidence, whereas abstention may follow from an omitted result state,
hidden property, or ambiguous requirement.

The reject option is particularly important because false positive verification
claims can be unsafe. A model that labels a requirement `FULFILLED` may cause a
reviewer to stop investigating. The thesis therefore reports false fulfillment
in addition to accuracy. At the same time, abstention is not automatically good.
A system could avoid errors by abstaining on every item. Abstention must be
interpreted together with coverage, accuracy, per-class performance, and the
reasons that produced it.

### 2.7 Synthesis of the Research Gap

Prior work establishes the relevance of requirements ambiguity, traceability,
GUI automation, multimodal software verification, UI-agent trajectories,
visual grounding, and abstention. No single line of work directly evaluates the
following contract: given a textual requirement and an already recorded ordered
UI flow, assign an application-specific fulfillment label, identify the
supporting or contradicting screenshot steps, optionally localize the evidence
within those screenshots, and preserve uncertainty about hidden or missing
states.

The research gap is therefore not the absence of multimodal models capable of
describing screenshots. It is the absence of a controlled, evidence-bounded
verification formulation that separates requirement semantics, flow coverage,
evidence traceability, and label aggregation. The following chapter formalizes
that formulation.

| Research area | Primary input | Typical output | Ordered evidence | Explicit verification uncertainty |
|---|---|---|---:|---:|
| Requirements traceability | Requirements and engineering artifacts | Trace links | Sometimes | Not usually a fulfillment label |
| GUI test automation | Executable UI and test oracle | Pass/fail and execution trace | Yes | Usually encoded as test outcome |
| Mind2Web-style UI agents | Task instruction and web trajectory | Next action or task success | Yes | Not the central output |
| SeeClick/UGround-style grounding | Instruction and UI image | Element or region | Usually no | Localization failure rather than requirement abstention |
| User-story/prototype support | User story and prototype | Story–prototype consistency | Usually static | Task-specific |
| This thesis | Requirement and recorded screenshot flow | Four-way label plus evidence | Yes | Explicit `ABSTAIN` and uncertainty reasons |

## 3 Research Design and Problem Formulation

### 3.1 Research Strategy

The thesis follows a design-and-evaluation strategy. It first defines a
verification contract and implements a modular system that realizes it. It then
constructs a reviewed benchmark and compares system configurations through
controlled experiments. Quantitative evaluation measures requirement labels,
evidence-step retrieval, cost, and stability. Qualitative analysis explains
which requirement structures and evidence patterns produce errors. Region
grounding and UI evaluability are evaluated as auxiliary components because
they affect traceability and the visible scope of the task.

The central unit of analysis is a verification item: one textual requirement
paired with one ordered screenshot flow and one reviewed reference decision.
Items from the same flow are not independent because they share screenshots and
application context. Statistical comparisons therefore resample complete flows
rather than individual requirements. With only 13 flow clusters, intervals are
reported as uncertainty summaries and interpreted cautiously.

The main evaluation is retrospective. The system does not control the website
or request new states; it judges an existing sequence. This choice makes the
visual evidence reproducible but limits conclusions to the recorded path. It
also makes it possible to evaluate failures of screenshot selection separately
from failures of visual interpretation.

### 3.2 Formal Task Definition

Let an ordered screenshot flow be

\[
F = \langle s_1, s_2, \ldots, s_n \rangle,
\]

where each \(s_i\) contains an image, a stable step index, and optional textual
metadata such as OCR or extracted page text. Let \(r\) be a textual
requirement. The verifier implements a mapping

\[
V(r, F) \rightarrow (y, E, C, U, q),
\]

where \(y\) is a requirement-level label, \(E\) is a set or ranking of evidence
units, \(C\) is an optional set of claim-level decisions, \(U\) contains
uncertainty reasons, and \(q\) is a rationale. The label belongs to

\[
Y = \{\texttt{FULFILLED},\ \texttt{PARTIALLY\_FULFILLED},\
\texttt{NOT\_FULFILLED},\ \texttt{ABSTAIN}\}.
\]

An evidence unit minimally identifies a screenshot step. It may additionally
contain a textual observation and one or more image regions. The ordering of
the flow is part of the input. Two flows containing the same screenshots in a
different order do not necessarily express the same interaction history.

The verifier is not asked whether the complete implementation satisfies the
requirement in every possible execution. It is asked what the available ordered
visual evidence establishes. Consequently, the target label combines the
requirement contract with an explicit evidence policy. This policy is supplied
to both the annotators and the evaluated models.

### 3.3 UI Evaluability

UI evaluability answers whether visible UI evidence can in principle resolve
the material obligations of a requirement. It is annotated separately from
fulfillment:

- `UI_VERIFIABLE` means that the material claims can be assessed through
  rendered interface content or visible state changes.
- `PARTIALLY_UI_VERIFIABLE` means that a material visible core exists but full
  satisfaction also depends on hidden state, persistence, policy, business
  logic, or an external system.
- `NOT_UI_VERIFIABLE` means that the central property has no stable visual
  manifestation or is too abstract for screenshot-based assessment.

Evaluability is a property of the requirement relative to the observation
modality, not a synonym for evidence availability in one particular flow. A
requirement can be UI-verifiable even when the recorded flow omits the needed
state. In that case the system should usually abstain because of a flow-coverage
gap. Conversely, a partially UI-verifiable requirement may receive a partial
label when its visible part is supported while a material hidden obligation
remains unresolved.

This distinction prevents two common errors. First, it stops the verifier from
interpreting hidden properties as if they were visible. Second, it prevents an
incomplete trajectory from redefining an otherwise observable requirement as
non-visual. Chapter 6 evaluates model agreement with the supplied evaluability
schema and stratifies verification errors by evaluability class.

### 3.4 Verification Label Semantics

`FULFILLED` is the strongest claim. It requires visible support for every
material UI-observable obligation, at least one recorded evidence unit, no
visible contradiction, and no unresolved material uncertainty about the
visible behavior. Routine implementation dependencies do not block fulfillment
when the requirement is explicitly satisfied by a visible success proxy. A
cart badge update, for example, can establish the requested visible cart state;
it does not prove database durability.

`PARTIALLY_FULFILLED` requires meaningful visible support for at least one
important claim and an unresolved missing, hidden, or ambiguous part. It is not
a lower-confidence form of `FULFILLED`. It describes a compound evidence state.
If a requirement asks for a search form and correct complete results, the form
may be visibly supported while correctness and completeness remain unverified.

`NOT_FULFILLED` requires visible counter-evidence against a central observable
claim. Missing evidence is insufficient. A requested control that is visibly
absent from the relevant complete state may justify the negative label, whereas
a flow that never visits that state does not.

`ABSTAIN` is used when the evidence cannot support a reliable positive, partial,
or negative decision. Reasons include textual ambiguity, unclear scope,
unresolved quantifiers, missing before/after states, unverified outcomes, and
nontrivial hidden properties. An abstention is a completed semantic prediction,
not a missing response.

### 3.5 Claims and Deterministic Aggregation

Long requirements may contain several obligations connected by conjunctions,
conditions, or outcome clauses. The pipeline may decompose a requirement into
claims \(C_r = \{c_1,\ldots,c_m\}\). Claim text is derived from the requirement
before the screenshots are interpreted. It must not encode what a particular
screen happens to show, because doing so would leak the evidence into the
contract.

Each claim receives one of the evidence statuses `SUPPORTED`,
`CONTRADICTED`, `MISSING`, `HIDDEN`, `AMBIGUOUS`, or `OUT_OF_SCOPE`. Claims may
also be marked as core or supporting obligations. A deterministic aggregator
then maps the collection of statuses and the requirement's UI evaluability to a
requirement label. In simplified form:

- all observable core claims supported and evidence present implies
  `FULFILLED`;
- supported and unresolved important claims imply `PARTIALLY_FULFILLED`;
- a contradicted observable core claim implies `NOT_FULFILLED`;
- insufficient, hidden, or ambiguous evidence without meaningful partial
  support implies `ABSTAIN`.

The aggregation rules reduce variation in how the final labels are interpreted,
but they cannot repair incorrect claim statuses. They also encode a normative
choice: visible contradiction is required for a negative decision. An offline
forced-decision counterfactual tests what happens when native abstentions are
instead converted to negative labels.

### 3.6 Evidence Contract

Evidence is represented at two granularities. Screenshot-step evidence links a
claim or requirement to one or more positions in the flow. Region-level
evidence localizes the relevant observation within a selected screenshot. These
levels answer different questions:

1. Did the system identify the correct state or transition?
2. Within that state, did it identify a relevant and sufficient visual region?

Step-level traceability is evaluated by ranked-retrieval metrics such as hit@k,
recall@k, and mean reciprocal rank. Region-level evidence is evaluated by
coordinate validity, applicability, coverage, relevance, and sufficiency.
Intersection over union is useful when a reference rectangle exists, but it is
not sufficient because several spatially different boxes may all provide valid
evidence.

Some claims are not reducible to one rectangle. A comparison may need two
regions, a transition may need two screenshots, and a screen-wide state may not
have a meaningful minimal box. The region-evaluation protocol therefore permits
`SINGLE_REGION`, `MULTI_REGION`, `WHOLE_SCREEN_OR_TRANSITION`, and
`NO_VISIBLE_REGION`. Returning no region is treated as a localization
abstention that can be correct when the claim has no visible support in the
selected screenshot.

### 3.7 Operationalization of the Research Questions

RQ1 is operationalized through matched full-coverage model runs using the same
258-item benchmark and supplied four-label semantics. The analysis reports
accuracy, macro-F1, per-class precision and recall, confusion matrices, false
fulfillment, abstention, agreement, cost, and run-to-run stability. A
deterministic baseline and a hosted open-weight model provide additional
reference points.

RQ2 is operationalized through a controlled two-by-two matrix. The claim factor
compares raw requirements with gated automatic decomposition. The screenshot
factor compares the complete ordered flow with lexical top-4 selection. Model,
prompt family, label schema, aggregation, batching policy, and benchmark are
held constant. Screenshot-step evidence and cost are outcomes alongside label
performance. Region grounding is reported separately and is not interpreted as
an accuracy intervention.

RQ3 uses a predefined error taxonomy applied to the frozen predictions.
Categories include over-fulfillment, hidden outcomes, quantifier and
completeness errors, missed late states, label-boundary disagreements, and
evidence-selection failures. Results are stratified by UI evaluability and
requirement pattern where sample sizes permit. The question characterizes
observed abstentions and unsafe positive decisions; it does not make a causal
claim that abstention itself improves safety.

### 3.8 Scope and Non-Claims

The task includes visible elements and text, navigation outcomes, short state
transitions, visible validation, and visible interaction results. Layout is in
scope when the requirement explicitly constrains it. Hidden backend correctness,
security guarantees, real payment processing, external delivery, global
availability, long-term persistence, and strict performance properties are out
of scope unless the requirement asks only for a visible representation.

The thesis does not claim formal verification, exhaustive testing, or
production readiness. It does not infer global absence from a finite flow and
does not treat a plausible interface as proof of an external effect. The
results characterize one reviewed benchmark of 13 web flows and must not be
generalized to all interfaces without further evaluation.

## 4 Verification Approach and Implementation

### 4.1 Architecture

The implemented system follows a modular pipeline:

\[
\text{flow ingestion} \rightarrow
\text{screen understanding} \rightarrow
\text{requirement understanding} \rightarrow
\text{evidence selection} \rightarrow
\text{claim verification} \rightarrow
\text{label aggregation}.
\]

The stages exchange typed structured records rather than unstructured chat
transcripts. Inputs preserve flow identifiers, step indices, screenshots, and
requirements. Outputs preserve labels, claims, evidence units, uncertainty
reasons, rationales, model metadata, and usage information. Dependency
injection allows the deterministic and multimodal components to be compared
without changing the surrounding data contract.

The evidence-first design is an engineering decomposition, not a claim that
every staged configuration is more accurate than a direct prompt. It makes the
points of failure inspectable: a requirement may be decomposed incorrectly,
the right screenshot may not be retrieved, the model may misread a visible
state, or the aggregator may map otherwise reasonable claim statuses to an
undesired final label.

### 4.2 Flow Ingestion and Screen Representation

A flow directory contains a stable flow identifier, ordered screenshot files,
task metadata, and step metadata. The ingestion layer preserves the recorded
step index and image dimensions. Original-resolution screenshots are retained
locally alongside processed assets so that evaluation can distinguish model
input resolution from review resolution.

Screen understanding constructs a lightweight representation for each step. It
can combine image metadata, available HTML-derived text, OCR sidecars, and
cached summaries. The textual representation supports inexpensive retrieval,
while the screenshot remains the authoritative visual input to the multimodal
verifier. A text match is never itself interpreted as proof of fulfillment.

Local flow material is separated from versioned annotations. A fresh checkout
contains code, requirements, manifests, and evaluation configuration, while the
Mind2Web source data must be obtained separately and exported into the expected
local structure. This separation supports the dataset redistribution boundary
described in Section 7.7.

### 4.3 Requirement Understanding

Requirement understanding performs two optional operations: UI-evaluability
classification and claim decomposition. The deterministic classifier uses
rules over the requirement text and serves as a low-cost baseline. The main
multimodal runs can instead request an evaluability judgment from the model.
Neither prediction is silently substituted for the reviewed reference during
evaluation.

The raw claim policy treats the complete requirement as one verification unit.
The gated policy applies deterministic decomposition only when the requirement
contains structures that plausibly benefit from splitting. In the final
benchmark it produces 281 claims from 258 requirements and splits 31
requirements. An LLM decomposition fallback exists in the general application
but is disabled in the controlled matrix so that hidden additional model calls
do not confound the comparison.

The repository also contains 541 reviewed benchmark claims. Supplying these
claims to the verifier creates an oracle or provided-claim condition. It is
useful for diagnosing claim-status prediction when the decomposition is fixed,
but it must not be reported as the performance of automatic decomposition.

### 4.4 Screenshot Selection

The retriever scores screenshot steps for each claim using the textual screen
representations. The default controlled policy is lexical retrieval, chosen
because it is deterministic, inexpensive, and easy to reproduce. Alternative
implementations support TF-IDF, local embeddings, and text-only LLM reranking,
but they are not mixed into the primary matrix.

For the top-4 condition, the four highest-ranked steps are selected for each
requirement or claim. Selected screenshots are grouped across several
requirements to reduce the number of API calls. Consequently, top-4 is a
retrieval limit at the item level, not necessarily a guarantee that every API
request contains only four distinct images.

The whole-flow condition attaches every screenshot in its recorded order. It
avoids retrieval omission but increases image input and irrelevant context. The
controlled comparison tests whether the smaller evidence set preserves labels
and traces at lower cost. Late-state failures are especially relevant because
lexical overlap may favor an early input form over a later result or summary
screen.

### 4.5 Multimodal Claim Verification

The multimodal verifier receives the supplied label schema, the requirement or
claims, ordered screenshots, and stable step identifiers. It returns structured
JSON containing UI evaluability where requested, claim statuses, evidence
steps, uncertainty reasons, rationales, and the fields needed for
requirement-level aggregation. Responses are validated before they enter the
evaluation. Missing or malformed items remain coverage failures rather than
being converted to semantic abstentions.

The final controlled matrix uses `gemini-3.1-flash-lite` with temperature zero,
thinking level `low`, fixed prompt and aggregation versions, and deterministic
chunks of at most eight requirements. Gemini 2.5 Flash-Lite provides a matched
low-cost model comparison with thinking budget zero. Qwen3-VL-8B-Instruct,
served through OpenRouter with provider fallbacks disabled, provides the hosted
open-weight baseline. Exact provider, model, parameters, execution date,
tokens, failures, and costs are archived according to the LLM reporting
guidelines used by the chair.

Gemini 3.1 Flash-Lite was selected as the primary experimental model because it
supports multi-image input and structured output, was available through the
existing verified adapter, and was inexpensive enough to run the complete
matrix and repetitions while holding the model fixed. Gemini 2.5 Flash-Lite was
selected as a deliberately cheaper earlier-generation sensitivity baseline
rather than a claim about frontier performance. The hosted Qwen model addresses
the methodological value of an open-weight comparison without implying full
local reproducibility. A local SmolVLM2 pilot was documented but not promoted
to a benchmark result because inference on the available hardware was too slow
and the capped response was incomplete.

The historical Gemini 3.1 Pro preview run is retained as contextual
strong-model evidence. It is not used as the primary model because its preview
status, cost, and earlier prompt and grouping configuration would confound a
full matrix comparison. This role-based selection prioritizes controlled
inference over a leaderboard-style collection of unrelated model outputs.

Temperature zero is not treated as a guarantee of determinism. The central
Gemini and Qwen configurations were therefore repeated. Each repetition uses a
separate output and cache directory, and the stability analysis distinguishes
label invariance from variation in cited evidence steps.

### 4.6 Label Aggregation

The label aggregator is deterministic and shared across the controlled
configurations. It receives claim statuses, claim importance, evidence
presence, uncertainty reasons, and effective UI evaluability. It enforces the
central safety gates: no `FULFILLED` label without evidence, no
`NOT_FULFILLED` label without a visible contradiction, and no fulfilled
decision while a material hidden property remains unresolved.

This separation reduces prompt dependence at the requirement-label boundary.
The model still determines the semantic claim statuses, so the aggregator does
not make the pipeline objectively conservative by itself. The weak
deterministic baseline demonstrates that poor upstream status decisions cannot
be repaired through aggregation alone.

The offline forced-decision analysis changes only the final policy applied to
frozen model outputs. It maps native abstentions to `NOT_FULFILLED` without
performing new inference. Because it cannot create a positive label, it is
interpreted as a closed-world counterfactual rather than a test of whether the
model learned to abstain.

### 4.7 Region-Level Evidence Grounding

Region grounding follows screenshot selection and semantic verification. Early
variants asked the multimodal model to emit normalized coordinates directly.
These boxes were unstable and sometimes landed on nearby text rather than the
specific evidence. OCR refinement improved text-aligned cases but could not
represent non-text controls or repair an incorrect semantic description.

The later candidate-mark pipeline generates candidate regions from OCR and UI
detectors, overlays stable identifiers, asks the multimodal model to select the
minimal evidence marks, and maps the selected identifiers back to pixel
coordinates deterministically. A grid can serve as a fallback when no suitable
candidate exists. Candidate generation and mark selection are separate sources
of error: proposal coverage limits the best achievable grounding result, while
the verifier may still choose the wrong available proposal.

The output permits zero, one, or several boxes per claim and supports an
explicit `NO_VISIBLE_REGION` response. Coordinates are stored together with the
image path, width, height, asset hash, coordinate space, and raw and refined
values where applicable. The review interface rescales boxes independently when
it displays a higher-resolution copy of the screenshot.

Bounding boxes are not expected to increase label accuracy in this thesis.
Their purpose is to make the evidence trace more precise and reviewable. The
evaluation therefore asks whether the regions are valid, relevant, and
sufficient, not whether the existence of a box caused a different
requirement-level prediction.

### 4.8 Annotation and Review Workbench

The project includes a local web workbench for browsing flows, reviewing
candidate and gold requirements, inspecting claims and evidence, running ad-hoc
verification, and comparing predicted regions with review judgments. Review
responses are stored separately from production outputs so that inspecting a
prediction does not silently overwrite the benchmark.

For UI-evaluability review, the interface hides the current label, model output,
fulfillment label, provenance, and annotator. Metrics remain hidden until the
target sample is completed. For region review, the reviewer first decides
whether local evidence is applicable and draws reference regions without seeing
the proposal. Only after locking this reference does the interface reveal the
predicted box for relevance and sufficiency assessment.

This two-phase design reduces anchoring on the model output. It does not by
itself create independent annotation; the reviewer identity, sampling process,
completion, and adjudication must still be reported.

### 4.9 Reproducibility and Artifact Management

Experiment configurations specify model identifiers, claim and screenshot
policies, retrieval parameters, generation settings, cost guards, and expected
coverage. Preflight manifests record the Git state, environment versions,
benchmark counts, gold hashes, prompt and source hashes, and exact commands.
Paid execution requires an explicit flag and a local cost ceiling. The ceiling
prevents accidental launches but is not a provider-side billing limit.

Run outputs archive structured predictions, raw responses, token usage, model
metadata, errors, and timing. Metrics are regenerated from matching gold and
prediction manifests rather than copied from historical summary files. The
curated thesis package contains aggregate metrics and frozen configuration but
excludes source screenshots and per-item raw interactions.

Automated tests cover schemas, aggregation gates, evaluation metrics, run
preparation, stability analysis, open-model adapters, and package auditing. Test
success supports implementation consistency; it does not substitute for
empirical validation of labels or evidence.

### 4.10 Implementation Boundaries

The system is a research prototype. Lexical retrieval is reproducible but not a
strong semantic retriever. OCR quality varies with resolution and interface
style. Hosted model behavior may change despite fixed identifiers, and
commercial APIs do not expose their complete serving stack. The local
open-weight pilot was too slow for a complete benchmark on the available
hardware, so the open-weight comparison uses hosted inference and reports this
limitation.

The architecture supports uploaded screenshot flows, but the thesis benchmark
is fixed to the reviewed Mind2Web-derived set. The implementation can display
region-level evidence even where a final human grounding evaluation is not yet
complete. Product functionality and validated scientific contribution are
therefore kept distinct throughout the following chapters.

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

The primary evidence unit for the label experiments is a screenshot step.
Evidence-step annotation is stable across the benchmark and directly represents
the ordered-flow setting. A step annotation identifies which screen contains
the observation, while a textual note describes the relevant visible content.
Region-level grounding is evaluated in a separate evidence-localization
analysis because a correct box is a different construct from a correct
requirement label or screenshot-step trace.

### 5.4 Running Example: Public Access to Amtrak Dining Information

The following requirement illustrates a clean positive case:

> The system shall make onboard dining information and café menu resources discoverable through public site navigation without requiring the user to sign in.

The requirement can be decomposed into two observable claims. First, onboard dining information and café menu resources are discoverable through public navigation. Second, the user is not required to sign in before reaching them. In the recorded flow, step 1 establishes the public site context, step 4 shows the Onboard Dining page and a route to the Café content, and step 5 shows the Café page and menu resources. The flow reaches these pages without displaying a sign-in wall. Both claims can therefore be supported by steps 1, 4, and 5.

The example is intentionally scoped to what the screenshots establish. A stronger requirement stating that route-specific menus are shown only when applicable would not be resolved by the same screenshots because no route context is visible. A requirement about account ownership checks would likewise refer to hidden access-control behavior. Small changes in wording can therefore change the correct label from `FULFILLED` to `PARTIALLY_FULFILLED` or `ABSTAIN`. This illustrates why requirement text, rather than the general intent imagined by the reviewer, must control the decision.

### 5.5 PURE as Exploratory External Material

PURE is a corpus of public requirements documents collected from heterogeneous sources and formats (Ferrari, Spagnolo, and Gnesi, 2017). Its documents are useful because their requirements are not generated from the screenshot trajectories used in the main benchmark. They are often longer, more formal, and dependent on headings, surrounding paragraphs, figures, or system context.

The current implementation can extract and contextualize selected PURE requirements and associate them with UI images embedded in or derived from the documents. The Split/Merge subset now contains 31 accepted verification items and 78 claims. Twenty-three items are attributed to Benno and eight retain Codex-draft provenance. The Mashboot subset contains 11 accepted items, but ten retain Codex-draft provenance and the annotation process began after predictions had been inspected. Acceptance status therefore does not make Mashboot blinded gold.

PURE can support qualitative discussion about context dependence, compound requirements, and UI verifiability. It cannot yet support a headline quantitative generalization claim. Some Split/Merge units are researcher-contextualized from descriptive document passages, and PURE figures usually express intended design rather than observed execution. Final inclusion requires provenance-aware reporting, independent review, a frozen extraction policy, and a clear distinction between document-to-UI consistency and implementation conformance.

### 5.6 Review Workflow and Quality Controls

Review is performed at several boundaries rather than through one final
accept/reject action. Candidate review checks whether the text is a meaningful
requirement, whether it is understandable outside the generation prompt, and
whether it refers to the intended application context. Verification review then
checks UI evaluability, label, claims, evidence steps, uncertainty reasons, and
rationale against the ordered flow.

The workbench validates structural constraints. A fulfilled item requires
evidence and may not contain a contradicted core claim. A negative item requires
visible counter-evidence. A partial item requires supported and unresolved
material content. An abstention requires an insufficiency reason. These checks
identify internally inconsistent records, but they cannot decide whether the
reviewer's interpretation of the screenshots is correct.

All 258 Mind2Web items received primary-author review. The repository records
review status and annotation provenance so that model-generated drafts are not
mistaken for independent gold. A separate 44-item sample was frozen for
independent verification-label review. It covers every flow and all four
requirement labels. Reviewer responses and adjudication are kept separate from
the original annotations, allowing agreement to be measured before the
reference is changed.

UI-evaluability and region-grounding reviews use their own targeted samples.
This separation is deliberate: agreement on a fulfillment label does not imply
agreement on whether the requirement is UI-verifiable, and agreement on the
correct screenshot does not imply that a predicted region is sufficient.

### 5.7 Benchmark Characteristics

The benchmark is organized by flow rather than as an unstructured pool. Items
within one flow share application context and screenshot evidence, which
creates statistical dependence. Flow identifiers are preserved in every
prediction and metric artifact so that evaluation can resample or diagnose at
the flow level.

The 541 reviewed claims exceed the number of requirements because compound
items contain multiple obligations. The distribution of claims is not uniform:
some requirements are atomic, while others describe an interaction and its
result, several visible fields, or a visible property combined with a hidden
outcome. This variation makes raw-versus-decomposed comparison meaningful but
also complicates claim matching.

Reference evidence may contain one step or several steps. Multiple steps are
common where a requirement concerns navigation, persistence across a short
interaction, or the difference between an input state and a result state. The
reference set is not assumed to enumerate every semantically valid alternative.
Automated overlap metrics are therefore complemented by qualitative review.

Every frozen run manifest records the expected requirement count and hashes of
the gold files. Evaluation rejects or reports missing predictions rather than
silently treating them as abstentions. This guard is necessary because several
historical repository metrics were produced after the gold set had grown and
therefore used incompatible denominators.

### 5.8 Data Governance

The 13 Mind2Web flows belong to the separately distributed `test_task` split.
Original screenshots, HTML, traces, videos, and unzipped test records remain
local. The repository can recreate the working flow set from identifiers after
the user obtains Mind2Web through the official source, but it does not mirror
the underlying test archive.

PURE source documents are likewise obtained from the original Zenodo record.
Because the curators note uncertainty about rights in the underlying documents,
the public artifact excludes PDFs, XML, figures, and substantial source text.
The full working repository is maintained under controlled access, while the
release candidate is limited to code, configurations, citations, and aggregate
results. Section 7.7 discusses the implications for reproducibility.

## 6 Evaluation

### 6.1 Compared Systems

The primary experiment covers all 258 verification items from flows 01–13.
Its central comparison is a two-by-two Gemini 3.1 Flash-Lite matrix in which
claim policy and screenshot policy are varied independently. The raw policy
treats each requirement as one unit, while gated decomposition splits selected
compound requirements. The all-screenshot policy supplies the complete flow,
while top-4 supplies the four screenshots selected by lexical retrieval. All
other recorded settings are held constant.

RQ1 additionally uses a matched Gemini 2.5 Flash-Lite raw/all run and a hosted
Qwen3-VL-8B-Instruct raw/top-4 run. The deterministic raw/top-4 and
gated/top-4 configurations provide non-LLM reference points. Historical Gemini
3.1 Pro and provided-claim runs remain useful sensitivity and oracle analyses,
but they are not inserted into the controlled matrix because their prompt,
claim, grouping, or grounding settings differ.

All headline comparisons require complete 258-item coverage. Missing model
outputs are counted as coverage failures and listed separately; they are not
converted to `ABSTAIN`. Exact model identifiers, dates, prompt versions,
generation parameters, image preparation, call counts, tokens, cost, failures,
fallbacks, and repository hashes are attached to the frozen run manifests.

An earlier controlled comparison over flows 01–10 and 201 items is retained as
development history. Every row in that comparison uses the same denominator,
which makes it internally interpretable, but the results are superseded by the
full-benchmark matrix for final RQ answers. Historical files that contain only
201 predictions must never be evaluated against the 258-item gold set.

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

### 6.5 Statistical Comparison and Run Stability

The primary comparisons are paired because every configuration predicts the
same requirements from the same flows. To preserve the dependence among items
within an application flow, uncertainty intervals are generated by resampling
the 13 complete flows with replacement. Each bootstrap replicate reconstructs
the compared result sets from the sampled flows and recalculates the metric
difference. The reported percentile intervals therefore describe variation
across the observed flow clusters rather than treating 258 correlated items as
independent.

The small number of clusters limits the precision of these intervals. They are
used to identify effects that are consistently visible across the current
flows, not to establish population-level guarantees. Per-flow metrics are
reported as diagnostics and are not treated as 13 independent benchmark
leaderboard entries.

Repeated runs evaluate operational stability. They reuse the frozen benchmark
and settings but write to independent caches and output directories. Pairwise
label agreement and Cohen's kappa summarize categorical stability; ranges of
accuracy, macro-F1, false fulfillment, and evidence MRR show whether headline
conclusions change. Repetitions are not additional test samples and are not
pooled to inflate the denominator.

### 6.6 UI-Evaluability Evaluation

UI evaluability is evaluated separately from fulfillment. The first analysis
compares the evaluability predicted in the realistic raw-requirement run with
the reviewed three-class labels. Because the class distribution is highly
imbalanced, raw agreement is accompanied by macro-F1, balanced accuracy,
per-class recall, unweighted Cohen's kappa, and ordinal-weighted kappa.

A deterministic text classifier provides a low-cost baseline. Its purpose is
not to establish a competitive model but to test whether simple lexical rules
capture the visible/hidden boundary. A high majority-class accuracy is
insufficient if the classifier fails to recognize partially or non-verifiable
requirements.

The reference labels are audited through a targeted blinded sample containing
all rare non-verifiable cases, structurally suspicious items, and stratified
controls. The reviewer sees the requirement and flow but not the existing
evaluability label, fulfillment label, model prediction, or provenance.
Disagreements are adjudicated before any reference updates. Mind2Web and PURE
results are reported separately because the latter contains intended-design
figures rather than executed trajectories.

The final analysis stratifies requirement-verification performance by
evaluability. It asks whether `PARTIALLY_UI_VERIFIABLE` and
`NOT_UI_VERIFIABLE` items produce more abstentions, partial labels, or unsafe
positive predictions. These strata are descriptive; the four-item
`NOT_UI_VERIFIABLE` group in the main benchmark is too small for a stable
standalone performance estimate.

<!-- Pending after blinded review:
Insert the completed 72-item audit agreement, class-wise results, adjudication
counts, and the final Mind2Web-only stratified verification table here. Do not
copy partial-review metrics into the thesis. -->

### 6.7 Region-Level Evidence Evaluation

Region grounding is evaluated as a traceability output, not as an intervention
on label accuracy. The evaluation unit is a claim, selected screenshot, and set
of predicted regions. Before seeing the prediction, a reviewer assigns one of
four applicability categories: `SINGLE_REGION`, `MULTI_REGION`,
`WHOLE_SCREEN_OR_TRANSITION`, or `NO_VISIBLE_REGION`. For applicable cases, the
reviewer draws one or more reference rectangles. The predicted regions are then
revealed and assessed for relevance and sufficiency.

The region analysis reports:

- coordinate validity and in-bounds rate;
- proposal coverage over localizable claims;
- relevance and sufficiency rates;
- maximum intersection over union and center-hit where reference rectangles
  make those measures meaningful;
- the frequency and correctness of `NO_VISIBLE_REGION`;
- results by text versus non-text evidence and by single- versus multi-region
  cases;
- additional calls, images, tokens, runtime, and cost;
- error categories such as wrong screenshot, wrong location, semantic error,
  box too narrow, box too broad, missing proposal, and unnecessary box.

The final sample is drawn from the frozen all-flow candidate-mark run and
stratified across all 13 flows and evidence types. Earlier direct-coordinate,
OCR, and single-flow candidate-mark reviews are retained as development
evidence, not pooled into one localization-accuracy estimate. A second reviewer
should label a representative subset so that agreement on applicability,
relevance, and sufficiency can be reported.

<!-- Pending after region review:
Insert the frozen sample size, sampling seed, completion and agreement, final
coverage/relevance/sufficiency metrics, confidence intervals where appropriate,
and two positive plus two failure examples. -->

### 6.8 Error-Analysis Protocol

The RQ3 analysis is performed on frozen predictions and a taxonomy fixed before
final counting. Each incorrect prediction and each unsafe `FULFILLED` decision
receives a primary error category and may receive secondary requirement-pattern
tags. Abstentions are coded separately so that a justified hidden-outcome
abstention is not grouped with a retrieval failure.

Model-error categories include schema violation, unsupported inference,
incorrect visible interpretation, and aggregation inconsistency. Evidence-error
categories include wrong screenshot, missed late state, incomplete multi-step
trace, and region-grounding failure. Requirement-pattern tags include
quantifiers, comparisons, persistence, external effects, result correctness,
compound obligations, absence claims, and ambiguous scope. Reference-label
disagreements are flagged rather than automatically counted as model errors.

The analysis reports denominators explicitly: frequency among all 258 items,
among incorrect predictions, among model abstentions, and among predicted
`FULFILLED` items as appropriate. Three to five frozen cases illustrate the
dominant mechanisms without substituting anecdotes for the coded counts.

### 6.9 Development-Stage Label Performance on Flows 01–10

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

### 6.10 Development-Stage Evidence Retrieval

Table 2 reports evidence metrics for the two configurations that currently have directly comparable step-level outputs.

**Table 2: Preliminary evidence retrieval results on 201 items from flows 01–10.**

| Configuration | MRR | Hit@1 | Hit@3 | Recall@1 | Recall@3 |
|---|---:|---:|---:|---:|---:|
| Gemini Flash Lite batched top-k | 0.582 | 0.473 | 0.657 | 0.260 | 0.485 |
| Deterministic baseline | 0.159 | 0.159 | 0.159 | 0.076 | 0.076 |

The batched top-k pipeline retrieves at least one gold evidence step in its first three predictions for approximately 65.7% of the items. Recall@3 is lower, at 48.5%, indicating that many multi-step evidence sets are incomplete even when one relevant screen is found. This distinction is important: verification may require a control state and a later result state, while hit@k is satisfied by retrieving either one.

The evidence results support the use of retrieval as a separately measurable component. They do not yet establish that top-k improves the final label. In fact, the current label results are weaker than the whole-flow baseline. Retrieval can help by concentrating model attention and reducing repeated image input, but it also creates a failure mode that the whole-flow prompt avoids: a decisive screenshot may never reach the verifier.

### 6.11 Dominant Error Patterns

The historical 13-flow review and the controlled runs reveal several recurring patterns. Exact category counts from the historical reports should not be mixed with the final controlled metrics because the underlying runs and gold snapshot changed. The patterns themselves are stable enough to guide the final analysis.

**Over-fulfillment.** The verifier frequently treats evidence for a visible entry point as evidence for the complete requirement. A search form becomes proof of correct search results, a link becomes proof of correct applicability, or one observed path becomes proof of a universal condition. This error directly increases false fulfillment.

**Hidden and external outcomes.** Requirements concerning persistence, availability, validity, delivery, payment, security, or backend correctness cannot usually be decided from the recorded screenshots. Models nevertheless prefer concrete labels and may infer an outcome from a UI proxy. The aggregation policy should preserve `HIDDEN` or `AMBIGUOUS` claim statuses and abstain when the hidden obligation is central.

**Universal and comparative language.** Terms such as “all,” “every,” “only,” and “always” require evidence across a defined domain. A finite flow often shows only one instance. Comparisons require both sides or a visible invariant across relevant states. The model tends to generalize beyond the observed example.

**Missing late states.** Cart, checkout, result, review, and summary evidence often appears near the end of a flow. A retriever dominated by lexical overlap may select an earlier screen containing the requirement vocabulary but omit the later screen that demonstrates the outcome.

**Boundary disagreements.** Some cases depend on the distinction between `PARTIALLY_FULFILLED` and `ABSTAIN`, or between `NOT_FULFILLED` and `ABSTAIN`. The adopted policy requires visible contradiction for `NOT_FULFILLED`. If a requested result state is not shown at all, abstention may be safer than a negative conclusion. If a visible entry point is supported but the result is unobserved, partial fulfillment may be more informative. These boundaries require explicit examples in the annotation guide and independent adjudication.

### 6.12 Late-State Failure Example

The Six Flags purchase flow (flow 10) provides a representative retrieval failure. Several requirements refer to quantity changes, combined cart contents, fees and totals, the ability to modify the cart, and controls visible before purchase confirmation. The decisive evidence appears in late steps, especially steps 8–10. Earlier evidence-selection variants often retrieved configuration or add-on screens but did not include the final cart summary.

This failure is not primarily a lack of visual intelligence. If the final cart screenshot is not supplied, the verifier cannot cite its subtotal, fee, tax, total, or modify-cart control. The resulting prediction may be `ABSTAIN` or `PARTIALLY_FULFILLED` even though the relevant visible state exists in the full flow. The example motivates retrieval rules that include action/result pairs, prioritize late screens for state-change requirements, or dynamically fall back to the whole flow when retrieved evidence is insufficient.

At the same time, always attaching the complete flow is not a free solution. Long flows increase image input, cost, and the amount of irrelevant content the model must inspect. The final evaluation should therefore treat retrieval as a trade-off among label quality, evidence recall, cost, and traceability rather than assuming that smaller top-k values are inherently better.

### 6.13 Current Controlled Full-Benchmark Comparison

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

### 6.14 Run-to-Run Stability

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

### 6.15 Preliminary UI-Evaluability Results

The realistic raw-requirement run predicts UI evaluability without receiving
the gold value in the prompt. On the 258 Mind2Web verification items, its raw
agreement with the current labels is 79.5%, macro-F1 is 0.420, unweighted
Cohen's kappa is 0.325, and ordinal-weighted kappa is 0.354. The aggregate
agreement is dominated by `UI_VERIFIABLE`: recall is 99.0% for this class,
24.2% for `PARTIALLY_UI_VERIFIABLE`, and 0% for the four
`NOT_UI_VERIFIABLE` items.

The result reveals a systematic tendency to treat a visible interface core as
evidence that the entire requirement is UI-verifiable. Requirements combining
visible interaction with persistence, completeness, external delivery, policy,
or backend correctness are consequently collapsed into the majority class.
This is relevant to RQ3 because the same hidden obligations can later produce
over-fulfillment or unstable boundaries between partial fulfillment and
abstention.

The deterministic text baseline confirms that overall accuracy is misleading.
On the broader 300-item accepted snapshot it reaches 72.7% accuracy but only
0.373 balanced accuracy, 0.322 macro-F1, and 0.010 Cohen's kappa. It predicts
the majority class for 284 items and does not correctly recover the
`PARTIALLY_UI_VERIFIABLE` class. Simple keyword rules are therefore
insufficient for the current three-way construct.

These figures remain preliminary with respect to reference quality. The
targeted blinded audit is prepared but not complete, and the 300-item baseline
mixes the main Mind2Web benchmark with exploratory PURE material. Final claims
must use the adjudicated Mind2Web labels and report PURE separately.

<!-- Pending final UI-evaluability results and performance stratification. -->

### 6.16 Preliminary Region-Grounding Findings

The grounding experiments establish that the system can produce and display
claim-specific evidence regions over complete flows. The July candidate-mark
run generated 588 stored evidence regions for 541 claim decisions. A later
fact-coverage run returned 697 stored regions and explicitly abstained with
`NO_VISIBLE_REGION` for claims where the selected screenshot did not contain a
defensible local region.

The development history also demonstrates why implementation coverage is not a
localization metric. In an early focused OCR inspection, 13 of 14 reviewed
proposals were marked `INCORRECT` and one `UNCERTAIN`. The lexical localizer
often selected a nearby heading or repeated keyword rather than the value,
range, control, or state that actually supported the claim. Higher image
resolution alone did not correct the free-form coordinates in a controlled
flow-01 pilot.

Later candidate-mark pilots produced substantially more valid regions on the
selected flows, indicating that constraining the model to explicit proposals is
promising. The currently reviewed portion of the all-flow V7 run contains 11
`VALID` and 2 `INCORRECT` judgments. This subset is too small and not
representative enough to estimate benchmark-wide grounding quality. Reviews
from earlier methods are not pooled because their candidate generators,
prompts, resolutions, flows, and inspection procedures differ.

The current evidence therefore supports two claims: region-level evidence is an
implemented output of the pipeline, and unconstrained or lexical coordinate
generation is unreliable. The final relevance, sufficiency, coverage, and
localization-abstention results remain dependent on completion of the frozen
review sample.

<!-- Pending final region-grounding table and reviewed examples. -->

## 7 Discussion and Threats to Validity

### 7.1 Interpretation and Practical Implications

The controlled results do not support a simple narrative in which more pipeline
stages necessarily improve verification. Supplying all screenshots with raw
requirements produces the highest accuracy in the primary Flash-Lite matrix.
Restricting input to lexical top-4 loses decisive information and saves almost
no money under the implemented batching strategy. Automatic decomposition
helps macro-F1 under restricted evidence but does not improve all-screenshot
accuracy and increases false fulfillment in that condition. These interactions
justify evaluating requirement understanding and screenshot selection as
separate factors.

The value of the evidence-first representation is instead clearest in
inspectability. The system records which screenshots were selected, which
claims were supported or unresolved, which uncertainty reason affected the
label, and where visible evidence was localized. This permits a reviewer to
distinguish a retrieval failure from a visual-reasoning failure or a
label-policy disagreement. A direct whole-flow prompt may produce a better
label while providing less diagnostic structure; these outcomes should not be
collapsed into one notion of quality.

For a practical deployment, the results favor an adaptive rather than fixed
retrieval policy. Complete flows are appropriate while flows remain short
enough for the model context and budget. Retrieval becomes useful when flows
grow, but it should monitor evidence sufficiency and fall back to additional
screens when outcome states, transitions, or multiple obligations are
unresolved. Late-screen priors and action/result pairing are concrete
improvements suggested by the observed failures.

The four-label schema is also application-dependent. A safety-critical
application may prefer more abstention, while another project may classify
missing required evidence as failure. The contribution is not that the chosen
labels are universally correct. It is that the schema is explicit, supplied to
the model, enforced consistently by aggregation, and evaluated with
safety-oriented metrics. This makes alternative risk policies comparable
without hiding them behind a binary accuracy score.

### 7.2 Internal Validity

All current Mind2Web verification items were reviewed by the primary author. Although the items are marked accepted, no inter-annotator agreement has been measured. Requirement labels, claim boundaries, and evidence sets may therefore reflect one reviewer's interpretation. A second reviewer should independently annotate a stratified sample covering all labels and major ambiguity categories. Disagreements should be adjudicated before the final runs.

The requirements are derived from the same flows against which they are evaluated. Human review and contrastive items reduce but do not eliminate circularity. Generated requirements may still emphasize properties that are easy to see in the source flow or mirror the assumptions of the generation model. Separate results for original and contrastive requirements and the exploratory PURE comparison can make this limitation more visible.

Model outputs are sensitive to model version, prompt text, image preparation, retries, and aggregation. Historical repository reports combine different current-per-flow runs and are useful for diagnosis but not controlled comparison. Final experiments require an immutable run manifest and exact model identifiers.

### 7.3 Construct Validity

The four labels operationalize a conservative interpretation of screenshot-based verification. Other projects might define missing evidence as failure or treat visible success messages as sufficient proof of a backend outcome. The thesis must present its label policy as a deliberate construct tied to the intended safety goal, not as the only possible definition.

Screenshot-step overlap is an incomplete measure of evidence quality. Human annotations may contain several valid screens, and a prediction may cite a semantically valid alternative that is absent from the reference set. Conversely, retrieving a gold step does not prove that the model used the correct region or interpretation. Manual evidence inspection should complement the automated metrics.

Region-level review introduces a related construct question. A visually tight
box is not necessarily the most useful explanation, and some claims require a
whole-screen state, multiple regions, or a transition. The grounding evaluation
therefore combines geometric measures with human relevance and sufficiency
judgments instead of defining correctness only through intersection over union.

UI evaluability is also a constructed boundary. The difference between a
routine hidden dependency behind a visible success proxy and a nontrivial
hidden property can depend on the application risk model. The label definitions
and examples must remain visible to both annotators and readers.

Claim matching introduces additional uncertainty. Two decompositions can be semantically equivalent while using different granularity. Low claim-status performance may reflect a poor decomposition, poor text matching, or poor status prediction. The final report should separate claim-match recall from status quality on matched claims.

### 7.4 External Validity

Thirteen web flows are a small sample of the variety of real interfaces and requirements. The selected tasks do not establish generalization to native mobile applications, desktop software, accessibility requirements, or industrial specifications. Mind2Web trajectories reflect one recorded interaction path and may omit alternative states relevant to a requirement.

PURE provides more realistic requirement documents but introduces a different limitation: screenshots or UI figures included in a requirements document typically describe intended behavior rather than observations of a running implementation. Verification against such figures may therefore assess document consistency rather than implementation conformance. The difference must be explicit if PURE is retained.

### 7.5 Reliability and Reproducibility

Model APIs can return malformed responses, change behavior between versions, or fail transiently. Older flow runs contained API fallbacks, and cached responses may hide differences between repeated executions. Final reporting should include retries, failures, fallbacks, token counts, image counts, runtime, cache policy, and pricing assumptions.

The repository contains stale summary metrics generated against older benchmark snapshots. For example, one stored batched-top-k metric reports 31.8% accuracy because it evaluates 201 predictions against all 258 current gold items and counts the 57 absent predictions as abstentions. Recomputed metrics restricted to the actual 201-item run give 75.1% accuracy. This discrepancy demonstrates why each thesis table must be generated from a frozen manifest with matching prediction and gold sets.

### 7.6 Current Scope Limitations

The pipeline provides mature step-level evidence and implemented region
grounding whose final human evaluation is reported separately once complete.
Bounding boxes are not treated as an accuracy intervention. Screenshots cannot
establish hidden backend truth, global absence, long-term persistence, external
delivery, or complete result correctness. The completed 2x2 matrix isolates
claim and screenshot policy for one model, but it does not show that
evidence-first design uniformly improves false fulfillment. These are
substantive boundaries and should not be hidden behind a general claim that
evidence grounding automatically makes the model safer.

### 7.7 Dataset Licensing and Artifact Availability

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

## 8 Conclusion

### 8.1 Summary

This thesis investigated automated verification of textual UI requirements
against ordered screenshot flows. The task was formulated as more than
multimodal label prediction: a defensible decision must remain bounded by the
available visual evidence, connect to identifiable UI states, and preserve
uncertainty when the flow does not establish the requirement.

To study this task, the thesis introduced an explicit four-label verification
contract, separated UI evaluability from fulfillment, implemented a modular
evidence-first pipeline, and constructed a reviewed 258-item benchmark over 13
Mind2Web-derived flows. The evaluation compared models, claim policies, and
screenshot-selection strategies while reporting label quality, unsafe positive
predictions, abstention, traceability, stability, cost, and qualitative error
patterns. A region-grounding extension adds spatially precise evidence without
being treated as a cause of improved label accuracy.

### 8.2 Answers to the Research Questions

For **RQ1**, multimodal models can apply the supplied application-specific
schema with useful but incomplete accuracy. Gemini 3.1 Flash-Lite reaches 79.5%
accuracy and 0.514 macro-F1 in the matched raw/all configuration, compared with
73.3% and 0.412 for Gemini 2.5 Flash-Lite. The hosted Qwen baseline shows that
equal headline accuracy can conceal substantially different false-fulfillment
and minority-class behavior. Model choice therefore matters, and accuracy alone
does not characterize schema compliance.

For **RQ2**, the effects of decomposition and screenshot selection are
conditional. Gated automatic decomposition does not materially improve
all-screenshot accuracy and increases false fulfillment in that setting, but it
improves macro-F1 when evidence is restricted to top-4. Lexical top-4 selection
reduces raw-requirement accuracy and evidence MRR relative to the complete flow
while providing negligible cost savings in the current batching
implementation. Explicit evidence remains valuable for traceability even where
the staged configuration does not improve labels. Region-level evidence is
evaluated as an additional traceability output rather than an accuracy factor.

For **RQ3**, the main failures are systematic. Models over-generalize from a
visible entry point to an unobserved outcome, infer hidden or external behavior
from interface proxies, overstate universal and comparative claims, and miss
decisive late states when retrieval favors lexical overlap. Native abstentions
often protect against unsupported closed-world decisions: replacing all
abstentions with negative labels substantially reduces accuracy. This does not
prove that every abstention is calibrated, but it confirms that insufficient
evidence and visible contradiction must remain distinct.

<!-- After the final audits, add one concise sentence to the RQ2/RQ3 answers
summarizing region relevance/sufficiency and UI-evaluability stratification. -->

### 8.3 Contributions

The first contribution is a problem formulation for evidence-bounded UI
requirement verification over ordered observations. It makes the visible/hidden
boundary and application-specific label policy explicit.

The second contribution is a working modular implementation covering flow
ingestion, requirement understanding, screenshot selection, multimodal claim
verification, deterministic aggregation, evidence localization, annotation,
and reproducible experiment packaging.

The third contribution is a reviewed benchmark with requirement labels, UI
evaluability, claims, evidence steps, rationales, uncertainty reasons, and
contrastive items. Its limitations—single-primary-author review, flow-derived
requirements, and class imbalance—are documented rather than hidden.

The fourth contribution is a controlled empirical evaluation showing that
decomposition and retrieval interact, that smaller screenshot sets can omit
decisive evidence without meaningful cost savings, and that model comparisons
must include minority labels and false fulfillment.

The fifth contribution is an inspectable error and evidence framework.
Screenshot-step retrieval, region grounding, UI evaluability, abstention,
runtime, cost, and stability are treated as distinct measurable properties.

### 8.4 Future Work

The immediate extension is broader independent annotation across flows,
applications, and requirement types. A larger number of flow clusters would
support more reliable statistical inference and make it possible to evaluate
rare negative and non-verifiable cases without extreme class imbalance.

Evidence selection should become adaptive. Temporal retrieval can explicitly
pair actions with result states, include late-state priors, and request
additional screenshots when selected evidence is insufficient. Semantic
retrieval may reduce lexical misses, but it must be evaluated against complete
flows rather than assumed to help.

Region grounding can be strengthened through higher-recall UI proposals,
specialized GUI grounders, and explicit handling of multi-region and transition
evidence. Its future value lies in reviewer efficiency, auditability, and error
localization, not necessarily in changing the requirement label.

Finally, the evaluation should expand beyond recorded web flows to native
mobile interfaces, industrial requirements, and repeatedly captured versions
of evolving UIs. Such settings would test whether the same evidence contract
supports regression analysis and human review in realistic development
workflows.

## References Used in This Draft

- Becker, J. et al. (2025). *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*. arXiv:2507.09089.
- Berry, D. M., Kamsties, E., and Krieger, M. M. (2003). *From Contract Drafting to Software Specification: Linguistic Sources of Ambiguity—A Handbook*. University of Waterloo Technical Report.
- Cheng, K. et al. (2024). *SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents*. ACL 2024. DOI: 10.18653/v1/2024.acl-long.505.
- Cleland-Huang, J. et al. (2014). *Software Traceability: Trends and Future Directions*. FOSE 2014. DOI: 10.1145/2593882.2593891.
- Deng, X. et al. (2023). *Mind2Web: Towards a Generalist Agent for the Web*. NeurIPS 2023. arXiv:2306.06070.
- Ferrari, A., Spagnolo, G. O., and Gnesi, S. (2017). *PURE: A Dataset of Public Requirements Documents*. IEEE RE 2017. DOI: 10.1109/RE.2017.29. Current dataset record: 10.5281/zenodo.7118517; original archived version: 10.5281/zenodo.1414117.
- Gervasi, V., Ferrari, A., Zowghi, D., and Spoletini, P. (2019). *Ambiguity in Requirements Engineering: Towards a Unifying Framework*. LNCS 11865, 191–210. DOI: 10.1007/978-3-030-30985-5_12.
- Gou, B. et al. (2025). *UGround: Universal Visual Grounding for GUI Agents*. ICLR 2025.
- Hendrickx, K. et al. (2024). *Machine Learning with a Reject Option: A Survey*. Machine Learning 113, 3073–3110. DOI: 10.1007/s10994-024-06534-x.
- Jimenez, C. E. et al. (2024). *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* ICLR 2024. arXiv:2310.06770.
- Kretzer, F., Kolthoff, K., Bartelt, C., Ponzetto, S. P., and Maedche, A. (2025). *Closing the Loop between User Stories and GUI Prototypes: An LLM-Based Assistant for Cross-Functional Integration in Software Development*. CHI 2025, Article 879. DOI: 10.1145/3706598.3713932.
- Kwa, T. et al. (2025). *Measuring AI Ability to Complete Long Tasks*. arXiv:2503.14499.
- Massenon, R., Gambo, I., and Khan, J. A. (2026). *Toward an Automated Cross-Multimodal Verification of Mobile App Bug Fixes*. Information and Software Technology 191, 107996. DOI: 10.1016/j.infsof.2025.107996.
- Nass, M., Alégroth, E., and Feldt, R. (2021). *Why Many Challenges with GUI Test Automation (Will) Remain*. Information and Software Technology. DOI: 10.1016/j.infsof.2021.106625.
- Rawles, C. et al. (2023). *Android in the Wild: A Large-Scale Dataset for Android Device Control*. NeurIPS 2023. arXiv:2307.10088.
- Wen, B. et al. (2025). *Know Your Limits: A Survey of Abstention in Large Language Models*. Transactions of the Association for Computational Linguistics 13, 529–556. DOI: 10.1162/tacl_a_00754.
- Yang, J. et al. (2023). *Set-of-Mark Prompting Unleashes Extraordinary Visual Grounding in GPT-4V*. arXiv:2310.11441.
- Zheng, B. et al. (2024). *SeeAct: GPT-4V(ision) is a Generalist Web Agent, if Grounded*. ICML 2024, PMLR 235.
