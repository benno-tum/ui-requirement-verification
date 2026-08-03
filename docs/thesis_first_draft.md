# Automated UI Requirement Verification from Ordered Screenshot Sequences

## Full Working Draft

**Status:** Working thesis prose, updated 24 July 2026. Chapters 1–8 contain
continuous draft text for the parts supported by the current implementation and
frozen experiments. Final independent-review results for UI evaluability and
region-level grounding are deliberately not anticipated. Non-rendered comments
mark the locations at which those results can be inserted after review. The
compiled LaTeX thesis and versioned evaluation artifacts are the quantitative
source of truth.

## 1 Introduction

### 1.1 Motivation

Large language models (LLMs) are used in software development for more than code completion. Coding agents can inspect repositories, edit multiple files, execute tools, and iteratively respond to test results. Kwa et al. (2025), for example, propose a task-completion time horizon that relates an agent's success to the time required by a human expert and report an approximately exponential historical increase on their studied software and reasoning tasks. Benchmarks such as SWE-bench have likewise moved evaluation from isolated code completion toward the resolution of real issues drawn from software repositories (Jimenez et al., 2024). These developments expand the scope of implementation work that can be delegated to models and make increasingly autonomous implementation workflows technically plausible.

Evidence for end-to-end productivity is less clear than benchmark progress. In
a randomized controlled trial, experienced open-source developers worked on
repositories they already knew. The early-2025 tools tested by Becker et al.
(2025) increased their task completion time. Benchmark capability and observed
delivery speed are thus separate empirical outcomes. Generated code still has
to be placed in repository context, checked against the intended behavior, and
reviewed.

This thesis starts from a narrower observation. When producing a candidate
implementation becomes cheaper, requirements clarification and verification
account for a larger share of the remaining effort. An agent can turn
underspecified text into code before the tacit clarifications of a development
team have occurred. A higher volume of generated changes also increases the
amount of behavior that must be checked. Faster implementation consequently
raises the value of precise requirements and efficient verification, even
though its effect on total engineering time varies between settings.

UI requirements expose this shift clearly because the contract and its evidence
use different modalities. The contract is usually written in natural language;
the evidence appears in visible states and transitions. For example, a
requirement may concern unauthenticated menu access, a filter that remains
selected, or fees displayed in a cart summary. No single source-code location
necessarily establishes any of these behaviors.

Manual review can interpret such behavior but takes time and may vary between
reviewers. Conventional GUI automation provides repeatable interactions when
an executable system, robust selectors, and explicit oracles are available.
Nass, Alégroth, and Feldt (2021) describe practical challenges arising from
the complexity and variability of graphical interfaces. Recorded screenshot
sequences preserve concrete states and their order without requiring a live
deployment. Their evidential scope is narrower: they contain one observed
trajectory and omit other reachable states and hidden implementation
properties.

### 1.2 Problem Statement

This thesis studies requirements-based review of UI flows. An ordered screenshot sequence records the successive interface states available to the reviewer and is paired with a collection of textual requirements. The screenshots are therefore the evidence representation for the review, rather than the object of the requirements themselves. For each requirement, the system should produce a verification label and point to the screenshot steps that justify its decision. The label set is `FULFILLED`, `PARTIALLY_FULFILLED`, `NOT_FULFILLED`, and `ABSTAIN`. The output may additionally contain smaller requirement claims, claim-level evidence statuses, uncertainty reasons, a natural-language rationale, and bounding boxes that localize visible supporting or contradicting evidence.

The technical problem is to construct a trace from the requirement to the
available evidence. Related work connects user stories with GUI prototypes,
performs agent-driven requirement verification in interactive GUIs, and
combines textual and visual evidence for mobile-app bug-fix verification
(Kretzer et al., 2025; Kolthoff et al., 2025; Massenon, Gambo, and Khan, 2026).
The setting studied here fixes the evidence artifact in advance as an ordered
set of UI states. Verification therefore requires a decision about
observability, identification of the relevant states, localization of evidence
within those states, and a boundary between visible support and inference.

The label boundary is clearest when a requirement explicitly asks for an
observable outcome. In one reviewed benchmark item, the flow shows a configured
eGift card and an `Add to Bag` control, but no updated bag or checkout state.
This supports the availability of the submission mechanism, not the requirement
that the configured card be added to the ongoing bag and proceed to checkout.
A `FULFILLED` label would therefore claim an outcome absent from the recorded
flow.

The label policy follows this evidential boundary. `FULFILLED` requires support
for all central observable parts. `NOT_FULFILLED` requires visible
counter-evidence; an omitted state is insufficient. Support for one material
part combined with a missing, hidden, or ambiguous part can justify
`PARTIALLY_FULFILLED`. When the flow supports no reliable positive or negative
decision, the output is `ABSTAIN`. This last case follows the reject-option
principle for decisions under insufficient information (Hendrickx et al.,
2024; Wen et al., 2025).

The task requires a boundary between visible UI behavior and hidden system
truth. Backend correctness, security guarantees, payment processing, email
delivery, database persistence, global result-set or data completeness,
long-term availability,
and external effects lie outside screenshot evidence unless the requirement
targets their visible representation. A success message can serve as a visible
proxy for the message shown to the user, without establishing the underlying
operation. Predictions and reference labels follow this boundary.

### 1.3 Research Gap and Approach

Existing work covers several neighboring tasks. Kretzer et al. (2025) connect user stories with GUI prototypes and study whether a story is represented in a prototype. More directly, GUISpector uses a multimodal agent to operationalize natural-language requirements, explore interactive GUI applications, record verification trajectories, and classify requirements as met, partially met, or unmet (Kolthoff et al., 2025). UI-agent datasets such as Mind2Web represent ordered interaction trajectories for language-conditioned action selection (Deng et al., 2023), while SeeClick studies the localization of interface elements from language instructions (Cheng et al., 2024). Cross-modal software-verification research also combines textual and visual artifacts to assess mobile-app bug fixes (Massenon, Gambo, and Khan, 2026). Requirements traceability explains why links between statements and artifacts matter, while abstention research explains why a model should sometimes decline a definite decision.

The evidence regime and output contract distinguish the setting studied here.
GUISpector creates evidence by operating an application; this thesis begins with
a previously recorded flow and asks what that fixed, incomplete record
establishes. Its label contract adds `ABSTAIN` and reserves `NOT_FULFILLED` for
visible contradiction, thereby separating insufficient evidence from
requirement violation. The task also differs from action selection and element
localization. Screenshot order matters whenever an action appears in one state
and its result in a later state.

The implementation converts each screenshot into a lightweight representation
and assesses the requirement's UI evaluability. Depending on the experimental
condition, it keeps the requirement intact or decomposes it into claims. A
retriever selects candidate steps, the multimodal verifier assigns claim
statuses, and deterministic rules aggregate them into a requirement label.
Stored intermediate outputs expose retrieval and reasoning errors separately.

“Evidence-first” names this architecture; its performance remains an empirical
question. In the current experiments, the staged configurations do not
consistently outperform direct whole-flow verification. Their demonstrated
benefit is diagnostic: evidence quality can be measured, and omitted states can
be distinguished from errors made after the correct state was supplied.

### 1.4 Research Questions

The thesis is organized around three research questions:

**RQ1: How well can multimodal models determine the fulfillment status of written requirements from ordered sequences of UI screenshots?**

RQ1 measures end-to-end agreement with the evidence-bounded four-label
operationalization defined in Section 3.4. The analysis uses accuracy,
macro-F1, per-class measures, confusion matrices, inter-model agreement, and
false fulfillment.

**RQ2: How do claim decomposition and screenshot selection affect label accuracy, evidence traceability, and cost relative to direct whole-flow verification?**

RQ2 varies claim decomposition and screenshot selection independently. A
controlled matrix compares raw and decomposed requirements under complete-flow
and shared top-k input. Label correctness, evidence overlap, runtime, token usage, and
cost are reported separately.

**RQ3: Which requirement and evidence patterns cause verification errors, abstentions, or unsafe `FULFILLED` predictions?**

RQ3 applies a predefined error taxonomy to schema violations, reasoning errors,
retrieval failures, insufficient evidence, and label-boundary disagreements.
The analysis covers universal and comparative wording, late result states,
hidden outcomes, and cross-step persistence. It characterizes observed
abstentions without assigning them a causal safety effect.

### 1.5 Contributions and Scope

The intended contributions of the thesis are:

1. A problem formulation for verifying textual UI requirements against ordered
   screenshot flows, including a separation between UI evaluability and
   fulfillment.
2. An evidence-first prototype that decomposes requirements, retrieves
   screenshot evidence, performs screenshot-grounded claim verification, and
   applies conservative aggregation.
3. A reviewed benchmark over 13 Mind2Web-derived flows containing requirement
   labels, claims, evidence steps, rationales, uncertainty reasons, and
   contrastive items.
4. An evaluation framework for label quality, false fulfillment, abstention,
   coverage, evidence retrieval, claim matching, runtime, and cost.
5. An empirical analysis of the requirement structures and flow patterns behind
   unsafe or uncertain decisions.

Screenshot-step evidence and region-level evidence are evaluated as two
different outputs. Screenshot-step retrieval is evaluated automatically against
the reviewed evidence steps. Region-level grounding is not treated as a cause of
better label accuracy; it is an additional traceability output whose relevance,
sufficiency, and coverage require human evaluation. The repository contains
candidate-mark grounding runs over all 13 flows and the review infrastructure
needed for this evaluation. PURE provides a separate exploratory
document-to-UI consistency analysis; the primary benchmark remains the 13
recorded execution flows.

The empirical scope is limited to 13 flows and does not establish industrial
readiness or broad generalization. The study makes the task and its failure
modes measurable, compares concrete verifier designs, and identifies the claims
supported by screenshot evidence.

The remainder of the thesis first establishes the conceptual and technical
foundations, formalizes the verification task, describes the implemented
pipeline, and then presents the benchmark, evaluation, results, limitations, and
conclusions.

## 2 Foundations and Related Work

The closest cross-artifact verification work was identified through a targeted
Google Scholar search on 30 July 2026. The search combined terms for
natural-language software artifacts, GUI or screenshot artifacts, and
multimodal verification. It was exploratory rather than a systematic
literature review and was supplemented by references from the identified
studies. The comparison focuses on work that connects textual
software-engineering artifacts with visual UI artifacts through a verification,
consistency, or grounding decision. The following sections also draw on the
supporting literatures on requirements quality, traceability, GUI testing,
interaction trajectories, visual grounding, and abstention.

### 2.1 Requirements as Verification Contracts

A software requirement states an obligation that an implementation is expected
to satisfy. Requirements may describe functionality, quality properties,
constraints, interactions, or externally visible outcomes. In practice, their
role is broader than that of natural-language documentation. They coordinate
expectations between stakeholders and provide the reference against which
design, implementation, and testing decisions are justified. Verification
depends on the implemented system as well as the precision and observability of
the requirement.

Natural-language requirements are attractive because stakeholders can read and
write them without committing to a formal notation. The requirements studied
here are natural-language artifacts and therefore retain ambiguities arising
from wording, domain context, and interpretation. Linguistic sources include
vague terms, implicit references, and underspecified quantifiers
[@berry2003; @gervasi2019]. Inspecting an implementation
cannot by itself resolve an underspecified target. If a requirement asks for
“all relevant results” without defining relevance, even complete access to the
UI would not establish a unique expected outcome.

Requirements retain their stated scope throughout the evaluation. Quantifiers
such as “all,” “only,” “always,” and “closest” can be supported when the
interface presents a bounded set as complete. Open or ambiguous domains require
uncertainty rather than an assumption that the observed cases are
representative. The exact decision rules are defined in Section 3.4.

UI requirements occupy a subset of software requirements.
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

Trace quality and classification accuracy are measured independently. Without
a trace, a reviewer has to repeat the complete inspection. A cited screenshot
step and region expose the observation on which the model relied. Correct
labels may still have incorrect traces, and correct traces may still be
interpreted incorrectly.

### 2.3 GUI Testing and Screenshot-Based Verification

GUI test automation normally executes interactions and checks explicit
assertions against a running system. It can provide strong evidence when the
environment, selectors, input data, and expected states are controlled. In
real-world systems, however, interfaces change, element locators become brittle,
external services introduce nondeterminism, and visually equivalent states may
have different internal representations. Nass, Alégroth, and Feldt (2021)
identify recurring GUI test-automation challenges that have persisted for many
years and argue that some are likely to remain.

The evaluation begins after a flow has been recorded and complements executable
GUI tests. The original application can be unavailable, and no interaction
script has to be replayed. A shared screenshot representation also permits
comparison across heterogeneous websites. The verifier does not execute the
application and therefore cannot observe backend state, network effects, or
paths outside the captured execution. For the Mind2Web benchmark, lexical
screenshot selection additionally uses visible-text candidates extracted from
recorded HTML metadata. This metadata ranks screenshots but is not treated as
fulfillment evidence: the multimodal verdict is based on the selected images
and image-derived OCR hints. The same selector can operate on OCR-only
representations, although screenshot-only inputs may provide a weaker retrieval
signal.

These omissions delimit the claims available from screenshots. A confirmation
message is evidence for the message, not for email delivery. A selected
checkbox says nothing about a later session, and one result page cannot
establish global completeness. The evaluation concerns conformance to the
recorded visual evidence.

Kretzer et al. (2025) provide a close requirements-oriented comparison by
connecting user stories to GUI prototypes and studying whether a story is
represented in the prototype. The present work differs by using ordered
observations of an executed interface, an explicit four-label contract, and
evidence links that may span multiple states.

Kolthoff et al. (2025) move closer to executable requirement verification.
GUISpector actively explores a GUI, records the resulting trajectory, and
returns evidence-backed met, partially met, or unmet decisions for requirements
and their acceptance criteria. This thesis instead holds the observed
trajectory fixed so that evidence selection and decisions under missing states
can be evaluated separately from the quality of an exploration policy. Its
four-label contract also represents insufficient evidence explicitly through
`ABSTAIN`.

Massenon, Gambo, and Khan (2026) study cross-modal verification of mobile-app
bug fixes and demonstrate the broader relevance of combining textual
engineering artifacts with visual evidence. Their task concerns bug-fix
consistency rather than requirement fulfillment, but it motivates treating
multimodal verification as a software engineering problem rather than generic
visual question answering.

### 2.4 Multimodal UI Agents and Interaction Trajectories

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
mark-selection step cannot return a relevant region that was omitted from the
candidate set. Mark density and placement may also obscure the interface.
SeeAct reports that Set-of-Mark was not its strongest strategy for web-agent
grounding and benefited from combining visual information with HTML-derived
candidates (Zheng et al., 2024).

The auxiliary candidate-mark implementation uses OmniParser-derived UI
proposals together with OCR candidates [@lu2024omniparser]. The main
label-evaluation matrix instead uses direct model-generated regions and does
not depend on candidate-mark grounding. The auxiliary variant is evaluated as
evidence localization. Coordinate validity covers only geometry; semantic
correctness additionally requires a region that is relevant to the claim and
sufficiently specific for review.

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
item. Those are coverage failures and must be reported separately. `ABSTAIN`
also differs from `NOT_FULFILLED`. The latter requires visible counter-evidence,
whereas abstention may follow from an omitted result state, hidden property, or
unresolved textual or evidence ambiguity.

False-positive `FULFILLED` verdicts can end a review prematurely. The evaluation
therefore reports false fulfillment alongside accuracy. An all-abstain system
would avoid many positive errors but provide no useful decisions. Coverage,
per-class performance, and recorded reasons therefore contextualize the
abstention rate.

### 2.7 Synthesis of the Research Gap

Taken together, these research strands establish the relevance of requirements ambiguity, traceability,
GUI automation, multimodal software verification, UI-agent trajectories,
visual grounding, and abstention. The work identified in the targeted search
does not directly evaluate the following contract: given a textual requirement and an already recorded ordered
UI flow, assess its fulfillment, identify the supporting or contradicting
screenshot steps, optionally localize the evidence within those screenshots,
and preserve uncertainty about hidden or missing states.

The reviewed multimodal systems can process screenshots, but the identified work does
not provide the full verification contract studied here. The missing elements
are a controlled formulation that separates requirement semantics, flow
coverage, evidence traces, and label aggregation. Chapter 3 defines this
formulation.

Table \ref{tab:research-gap-comparison} makes the boundary to adjacent research
areas explicit. The central distinction is the combination of an ordered
evidence trace with a fulfillment decision. Explicit abstention and uncertainty
reasons add diagnostic context but are not treated as a separate research
contribution.

\begin{table}[htbp]
  \centering
  \footnotesize
  \setlength{\tabcolsep}{4pt}
  \begin{tabular}{@{}>{\raggedright\arraybackslash}p{0.20\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.14\linewidth}>{\raggedright\arraybackslash}p{0.22\linewidth}@{}}
    \toprule
    \textbf{Research area} & \textbf{Primary input} & \textbf{Typical output} &
    \textbf{Ordered evidence} & \textbf{Explicit abstention or uncertainty} \\
    \midrule
    \textbf{Requirements traceability} & Requirements and engineering artifacts & Trace links & Sometimes & Not usually a fulfillment label \\
    \textbf{GUI test automation} & Executable UI and test oracle & Pass/fail and execution trace & Yes & Usually encoded as test outcome \\
    \textbf{Mind2Web-style UI agents} & Task instruction and web trajectory & Next action or task success & Yes & Not the central output \\
    \textbf{Visual UI grounding} & Instruction and UI image & Element or region & Usually no & Localization failure rather than requirement abstention \\
    \textbf{User-story/prototype support} & User story and prototype & Story--prototype consistency & Usually static & Task-specific \\
    \midrule
    \rowcolor{TUMLightGray!30}
    \textbf{This thesis} & \textbf{Requirement and recorded screenshot flow} &
    \textbf{Four-way label plus evidence} & \textbf{Yes} &
    \textbf{Explicit \texttt{ABSTAIN} and uncertainty reasons} \\
    \bottomrule
  \end{tabular}
  \caption{Comparison of adjacent research areas with the verification contract studied in this thesis.}
  \label{tab:research-gap-comparison}
\end{table}

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
application context. Statistical comparisons therefore use a cluster bootstrap
that resamples complete flows rather than individual requirements
[@fieldwelsh2007]. With only 13 flow clusters, intervals are
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
V(r, F) \rightarrow (y, a, E, C, U, q),
\]

where \(y\in Y\) is a requirement-level label, \(a\in A\) is a UI-evaluability
decision, \(E\) is a set of evidence units, \(C\) is an optional set of
claim-level decisions, \(U\) contains uncertainty reasons, and \(q\) is a
rationale. The labels belong to

\[
Y = \{\texttt{FULFILLED},\ \texttt{PARTIALLY\_FULFILLED},\
\texttt{NOT\_FULFILLED},\ \texttt{ABSTAIN}\}.
\]

\[
A = \{\texttt{UI\_VERIFIABLE},\
\texttt{PARTIALLY\_UI\_VERIFIABLE},\
\texttt{NOT\_UI\_VERIFIABLE}\}.
\]

Together, \(y\) and \(a\) distinguish two reasons why a requirement may not
receive `FULFILLED`: the recorded flow may omit evidence for an otherwise
UI-verifiable requirement, or the requirement may contain obligations that
screenshots cannot resolve in principle.

An evidence unit minimally identifies a screenshot step and may additionally
contain a textual observation and one or more regions, represented by bounding
boxes and region metadata. The ordering of the flow is part of the input. Two
flows containing the same screenshots in a different order do not necessarily
express the same interaction history.

The target is the conclusion supported by the recorded visual evidence. It does
not cover every possible execution of the implementation. The label therefore
depends on the written requirement and the evidence policy supplied to
annotators and models.

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

For the complete operational definitions, uncertainty reasons, and consistency
gates, see Appendix A.

Evaluability is a property of the requirement relative to the observation
modality, not a synonym for evidence availability in one particular flow. A
requirement can be UI-verifiable even when the recorded flow omits the needed
state. Its fulfillment label then depends on the evidence that remains;
`ABSTAIN` is appropriate only when the flow supports no reliable positive,
partial, or negative decision. Conversely, a partially UI-verifiable
requirement may receive a partial label when its visible part is supported
while a material hidden obligation remains unresolved.

Separating evaluability from fulfillment keeps hidden properties outside the
visible contract while preserving the difference between an unobservable
requirement and an incomplete trajectory. Chapter 6 measures agreement with the
evaluability schema and stratifies verification errors by class.

### 3.4 Verification Label Semantics

`FULFILLED` is the strongest claim. It requires visible support for every
material UI-observable obligation, at least one recorded evidence unit, no
visible contradiction, and no unresolved material uncertainty about the
visible behavior. Routine implementation dependencies do not block fulfillment
when the requirement is explicitly satisfied by a visible success proxy. A
cart badge update, for example, can establish the requested visible cart state;
it does not prove database durability.

`PARTIALLY_FULFILLED` describes a compound evidence state: at least one
important claim has visible support, while another remains missing, hidden, or
ambiguous. For a requirement covering both a search form and complete correct
results, the form can be supported even when result correctness and
completeness remain unverified.

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

The aggregation rules standardize final-label interpretation but cannot repair
incorrect claim statuses. They encode the additional policy choice that a
negative decision requires visible contradiction. An offline counterfactual
tests the alternative of converting native abstentions to negative labels.

### 3.6 Evidence Contract

Evidence is represented at two nested granularities. Step-level evidence
identifies the relevant screenshot or transition. Region-level evidence can
then refine that trace by localizing an observation within a selected
screenshot. In the final multimodal runs, step indices, textual observations,
and optional regions are returned jointly in the same model response, but their
quality is evaluated separately:

1. Did the system identify the correct state or transition?
2. Within that state, did it identify a relevant and sufficient visual region?

Step-level traceability is evaluated through overlap between returned and
reviewed evidence steps. The evaluator reports hit@k, recall@k, precision@k,
and a reciprocal first-hit summary. Requirement-level evidence is normalized
into chronological step order, so position-based values describe alignment of
the ordered trace rather than a confidence or lexical-retrieval ranking.
Region-level evidence is evaluated by coordinate validity, applicability,
coverage, relevance, and sufficiency.
Intersection over union is useful when a reference rectangle exists, but it is
not sufficient because several spatially different boxes may all provide valid
evidence.

Some claims are not reducible to one rectangle. A comparison may need two
regions, a transition may need two screenshots, and a screen-wide state may not
have a meaningful minimal box. The region-evaluation protocol therefore permits
four reference types:

- `SINGLE_REGION` for one localized area;
- `MULTI_REGION` for evidence distributed across several areas;
- `WHOLE_SCREEN_OR_TRANSITION` for screen-wide or temporal evidence; and
- `NO_VISIBLE_REGION` when no localizable visible support exists.

The last category records a valid localization abstention because the claim has
no localizable visible support. Returning no region for any other category is a
localization failure.

### 3.7 Operationalization of the Research Questions

Matched full-coverage runs on the 258-item benchmark answer RQ1. Accuracy,
macro-F1, class-specific scores, confusion matrices, false fulfillment,
abstention, agreement, cost, and run stability cover different aspects of
fulfillment assessment. The deterministic and hosted open-weight baselines
provide reference points. RQ1 additionally compares matched configurations
across different models to assess model sensitivity.

For RQ2, a controlled two-by-two matrix crosses raw versus gated-decomposed
requirements with complete-flow versus shared lexical top-4 screenshots. Model, prompt
family, label schema, aggregation, batching, and benchmark remain fixed.
Screenshot-step traceability and cost are evaluated alongside labels. The
separate region-grounding analysis does not enter the accuracy comparison.

RQ3 applies a predefined taxonomy to frozen predictions. A screenshot-aware
coding pass assigns one primary outcome and optional pattern tags, while a
deterministic heuristic serves only as a separate consistency check. Counts are
descriptive for the reviewed flows and do not support population-level or
causal claims.

### 3.8 Scope and Non-Claims

The task covers visible content, controls, navigation outcomes, short state
transitions, validation, and visible interaction results. It does not establish
hidden backend correctness, security, external delivery, global availability,
long-term persistence, or strict performance properties unless a requirement
concerns only their visible representation. Accordingly, the study provides
neither formal verification nor exhaustive testing; it evaluates what a finite
recorded flow supports.

## 4 Verification Approach and Implementation

### 4.1 Architecture

Figure \ref{fig:evidence-first-architecture} shows the implemented system as a
UML-style component architecture. Dashed subsystem boundaries separate input
preparation, evidence reasoning, and decision and trace generation. The
solid connectors denote verdict-bearing component dependencies. Dashed
connectors distinguish the localization trace: the region grounder is a
first-class component, but its coordinates are carried through aggregation as
evidence metadata rather than used to determine the requirement label.

\begin{figure}[htbp]
  \centering
  \resizebox{\textwidth}{!}{\input{figures/evidence_first_architecture}}
  \caption{UML-style component view of the evidence-first verifier. Dashed
  boundaries group related components; solid connectors show verdict-bearing
  dependencies, while dashed connectors carry region-level trace metadata.}
  \label{fig:evidence-first-architecture}
\end{figure}

Each component consumes and emits typed structured records rather than an
unstructured chat transcript. Inputs preserve flow identifiers, step indices,
screenshots, and requirements. Outputs preserve labels, claims, evidence
units, uncertainty reasons, rationales, model metadata, and usage information.
This record contract is already represented by the component dependencies in
Figure \ref{fig:evidence-first-architecture}; a second linear data-flow diagram
would repeat the same transformation at a different level of abstraction.

Dependency injection allows the deterministic and multimodal components to be
compared without changing this data contract.

The staged architecture exposes four failure locations: claim decomposition,
screenshot retrieval, visual interpretation, and final aggregation. Its
purpose is diagnostic. Accuracy relative to a direct prompt is measured in the
experiments rather than assumed from the architecture.

### 4.2 Flow Ingestion and Screen Representation

A flow directory contains a stable flow identifier, ordered screenshot files,
task metadata, and step metadata. The ingestion layer preserves the recorded
step index and image dimensions. Original-resolution screenshots are retained
locally alongside processed assets so that evaluation can distinguish model
input resolution from review resolution.

Screen understanding constructs a lightweight representation for each step. In
the main benchmark, it records image dimensions and extracts visible-text
candidates from the available Mind2Web HTML metadata. Existing OCR sidecars are
added where available. The resulting text supports inexpensive retrieval, while
the screenshot remains the authoritative visual input to the multimodal
verifier. A text match is never itself interpreted as proof of fulfillment.

Local flow material is separated from versioned annotations. A fresh checkout
contains code, requirements, manifests, and evaluation configuration, while the
Mind2Web source data must be obtained separately and exported into the expected
local structure. This repository layout implements the redistribution boundary
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

For the top-4 condition, lexical retrieval first produces item-level candidate
steps. For each verification batch of up to eight items, these candidates are
then compressed into a shared set of at most four attached screenshots. The
condition therefore evaluates retrieval together with batch-level evidence
compression; it does not guarantee four independently selected screenshots for
each requirement or claim.

The evaluated flows do not require retrieval to fit within the model input
limit. The longest flow contains 19 screenshots and remains well within this
limit. Shared top-k selection instead places a fixed bound on the visual input and
produces an explicit evidence ranking. The comparison tests whether this
smaller evidence set preserves labels and traces at lower cost without omitting
decisive screenshots. These properties may become more important for longer
flows or models with smaller context windows.

The capacity check used during system design reaches the same conclusion. Even
a conservative 1,000-line, 20-screenshot stress case fits within the documented
native context of Qwen3-VL-8B-Instruct and the input limits of Gemini 2.5
Flash-Lite and Gemini 3.1 Flash-Lite [@qwen3vl8b2025;
@googlegemini25flashlite2026; @googlegemini31flashlite2026]. Retrieval is
consequently evaluated as a bounded evidence and efficiency policy, not as a
necessary workaround for the present benchmark. Section 6.3 reports whether
that policy preserves decisive evidence and reduces end-to-end cost.

The whole-flow condition attaches every screenshot in its recorded order. It
avoids retrieval omission but increases image input and irrelevant context. The
late-state failures are especially relevant because lexical overlap may favor
an early input form over a later result or summary screen.

A separate order-unavailable robustness condition keeps the screenshot set,
requirements, model, chunking, label contract, and aggregation matched to the
raw whole-flow condition. For each flow, a fixed recorded permutation changes
the attachment order and replaces original step identifiers with local apparent
identifiers. The prompt discloses that the original chronology was removed by
the test environment and instructs the model not to invent before/after
relations. OCR and image metadata remain attached to the corresponding image,
and cited apparent identifiers are mapped back to original flow steps before
evidence scoring. This manipulation tests verification when trustworthy temporal
order is unavailable; it does not deceive the model with a false chronology.

### 4.5 Multimodal Claim Verification

The multimodal verifier receives the fixed label definitions, the requirement
or claims, ordered screenshots, and stable step identifiers. It returns
structured JSON containing UI evaluability where requested, claim statuses,
evidence steps, uncertainty reasons, rationales, and the fields needed for
requirement-level aggregation. Responses are validated before they enter the
evaluation. Missing or malformed items remain coverage failures rather than
being converted to semantic abstentions.

The final controlled matrix uses `gemini-3.1-flash-lite` with temperature zero,
thinking level `low`, fixed prompt and aggregation versions, and deterministic
chunks of at most eight requirements. Gemini 2.5 Flash-Lite provides a matched
low-cost model comparison with thinking budget zero. Qwen3-VL-8B-Instruct,
served through OpenRouter with provider fallbacks disabled, provides the hosted
open-weight baseline. Exact provider, model, parameters, execution date,
tokens, failures, and costs are archived following the reporting guidelines
for empirical software-engineering studies involving LLMs proposed by Baltes
et al. (2026).

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

The historical Gemini 3.1 Pro preview run provides contextual strong-model
evidence. Its preview status, cost, and earlier prompt and grouping
configuration prevent its use in the controlled matrix. The model set was
chosen for matched comparisons rather than leaderboard coverage.

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

Deterministic aggregation reduces prompt dependence at the requirement-label
boundary. The model still determines the semantic claim statuses, and poor
upstream decisions remain unrecoverable. The weak deterministic baseline
demonstrates this limitation.

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

Bounding boxes provide a more precise evidence trace. Their evaluation measures
geometric validity, relevance, and sufficiency. Label accuracy remains outside
this comparison because region generation is not used as an accuracy
intervention.

### 4.8 Annotation and Review Workbench

The project includes a local web workbench for browsing flows, reviewing
candidate and gold requirements, inspecting claims and evidence, running ad-hoc
verification, and comparing predicted regions with review judgments. Review
responses are stored separately from production outputs so that inspecting a
prediction does not silently overwrite the benchmark.

The UI-evaluability audit presents every case in which the stored author label
differs from the deterministic classifier. It shows both labels, the
classifier's triggered hidden-property terms, the author annotation note, claim
composition, and a generated diagnostic hypothesis. The author then records a
resolution and whether a later reference amendment is recommended. The region
audit has a different purpose: it shows the frozen V7 regions and asks whether
they are geometrically valid, semantically relevant, and sufficient for the
stated claim.

Both audits are performed by the thesis author. Their samples target observed
disagreements and predicted regions, so their results are reported as
qualitative boundary and output analyses. These diagnostic audits are separate
from the prediction-independent reference-annotation workflow and do not
define the labels used in the headline comparisons.

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

The main evaluation data consists of 13 web interaction flows derived from the Mind2Web dataset. Mind2Web was originally introduced as a benchmark for generalist web agents and contains real website tasks and interaction trajectories (Deng et al., 2023). In this study, ordered screenshots from selected trajectories serve as observations for independently represented UI requirements; the original action-prediction task is not evaluated.

The 13 flows form a purposive convenience sample from 39 locally processed
flows. They were selected for complete screenshot sequences and coverage of
search, navigation, forms, carts, checkout, and result states; they are neither
random nor representative of web interfaces in general. The sample covers
theme-park purchases, product lookup, careers navigation, dining information,
cinema support forms, cruise search, book search, and business listings. Each
flow contains several meaningful states. A
cart flow may progress from product selection through quantity changes and
add-ons to the summary and checkout controls. Search flows contain inputs and
later results. These sequences support requirements that a single screenshot
cannot resolve.

The benchmark contains 258 verification items across the 13 flows. Of these,
187 are reviewed source requirements derived from the recorded flows. The
remaining 71 are reviewed contrastive requirements: text-only variants proposed
from the source requirements and broader hypotheses about similar systems, then
reviewed against the screenshots. Their annotations contain 541 claims. All
items completed a prediction-independent primary-author review workflow. A
later qualitative grounding audit exposed one internally inconsistent GameStop
annotation. The resulting post-hoc author amendment is logged in the item
metadata; all reported metrics were recomputed against the corrected reference
while leaving stored model predictions unchanged.

The label distribution is imbalanced: 172 items are `FULFILLED`, 44 are `PARTIALLY_FULFILLED`, 33 are `ABSTAIN`, and 9 are `NOT_FULFILLED`. Approximately two thirds of the items are therefore positive. This skew is consistent with deriving requirements from observed, functioning UI flows, but it is not an estimate of label prevalence in production systems. A classifier that favors `FULFILLED` can still obtain a deceptively strong accuracy while failing on the three less frequent labels. This imbalance motivates macro-F1 and per-class reporting.

UI evaluability is annotated separately from fulfillment. The 258 items include
220 `UI_VERIFIABLE`, 35 `PARTIALLY_UI_VERIFIABLE`, and 3
`NOT_UI_VERIFIABLE` cases. Evaluability describes whether screenshots can
resolve the requirement in principle; the final label describes what the
recorded flow supports. A requirement may therefore be UI-verifiable in
principle even when the recorded flow does not contain enough evidence for a
decision.

### 5.2 From Candidates to Verification Gold

Because requirements are derived from UI flows, benchmark construction uses
staged artifacts and prediction-independent human review to separate candidate
generation from reference annotation.

Harvesting uses the recorded UI flows to produce a broad set of requirement
hypotheses, including redundant, ambiguous, hidden, and incompletely supported
properties. Filtering and rewriting convert selected hypotheses into
candidates. A reviewer then rejects, edits, or promotes each candidate;
candidate status carries no correctness claim. Because these hypotheses are
derived from observed UI states, harvesting alone tends to produce requirements
that the same flows fulfill.

Items with the explicit `contrastive` tag form the 71 contrastive cases; the
other 187 items form the source set. Review promotes a text into the benchmark
and adds UI evaluability, a requirement-level label, atomic claims, claim
statuses, evidence steps, rationale, and uncertainty reasons.

Contrastive requirements are used to increase difficulty and improve label
coverage. Their generation receives the reviewed source requirements and task
context, but no screenshots. A contrastive item may strengthen a visible
requirement with a completeness condition, add a hidden persistence obligation,
require a comparison that the flow does not show, or request a control that is
visibly absent. The proposed contrast and intended label are only suggestions.
They become benchmark reference data after review against the requirement
wording and the screenshots.

Figure \ref{fig:benchmark-construction-funnel} summarizes this construction and
keeps generated proposals separate from reviewed reference data.

\begin{figure}[htbp]
  \centering
  \resizebox{\textwidth}{!}{\input{figures/benchmark_construction_funnel}}
  \caption{Construction of the 258-item verification benchmark. Generated
  source candidates first enter source review. The resulting reviewed source
  set then seeds contrastive generation, whose variants undergo a separate
  evidence review before entering the verification gold.}
  \label{fig:benchmark-construction-funnel}
\end{figure}

The resulting set contains more than straightforward positive descriptions, but
its construction introduces dependencies. Source requirements and verification
evidence originate from the same flows, and contrastive generation may
emphasize particular hard cases. The primary-author reference review was
performed independently of the evaluated model predictions. Source and
contrastive requirements are reported separately where their construction is
relevant, and flow-level resampling preserves the benchmark's clustered
structure.

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

### 5.4 Quantified Counterexample: GameStop Store Synchronization

The following contrastive requirement illustrates why quantifier scope changes
the label even when most visible UI state is correct:

> The system shall keep the searched location, selected radius, and resulting stores synchronized between the map view and the store list.

Step 4 retains the search location 90028 and a 15-mile radius, and the map is
centered on Los Angeles. Most visible results are also in the Los Angeles area.
The first result, however, is the pinned Polaris Fashion Place Mall home store
in Columbus, Ohio. The core claim states that *all* returned store results must
match the searched map context. One visible counterexample therefore
contradicts that universal claim and yields `NOT_FULFILLED`; it is not an
accepted caveat and does not require inspection of the last list entry.

\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.96\textwidth]{figures/gamestop_quantifier_counterexample.png}
  \caption{Two-region evidence for the quantified GameStop counterexample.
  Region A is the Los Angeles map context selected as OmniParser candidate
  \texttt{U44}; region B is OCR candidate \texttt{T108}, which contains the
  conflicting address ``COLUMBUS, OH 43240.'' Together they localize both sides
  of the contradiction without treating the sixth visible store title as
  evidence of completeness.}
  \label{fig:gamestop-quantifier-counterexample}
\end{figure}
\clearpage

### 5.5 Running Example: Amtrak Navigation

The following requirement illustrates a clean positive case:

> The system shall expose major travel experience categories from the primary site navigation.

This is Amtrak `REQ-01` in the reviewed benchmark. Step 1 shows the
Experience entry in the primary navigation, and step 2 shows its expanded menu
with the major travel-experience categories. Both claims are directly visible,
so the accepted label is `FULFILLED`.

\begin{figure}[htbp]
  \centering
  \resizebox{0.94\textwidth}{!}{\input{figures/amtrak_running_example}}
  \caption{Running verification example. Step 1 exposes the Experience entry in
  the primary navigation, while step 2 exposes the corresponding travel
  categories.}
  \label{fig:amtrak-running-example}
\end{figure}

The same menu would not establish that every experience category has a complete
detail page or that access-control rules are enforced. Such stronger wording
would require additional evidence and could justify a partial or abstaining
decision.

### 5.6 Wording and Temporal Scope: Book Depository

A Book Depository pair makes this wording boundary concrete while holding the
application, screenshots, and visible data constant. Both items use steps 3
and 4, where the author criterion “Stephen King” remains in the advanced search
form and “German” is added as a language criterion. The pair is a supplementary
annotation example, not one of the five prespecified RQ3 cases; its inclusion
does not change the taxonomy or the reported category counts.

- `REQ-08` — `FULFILLED`: “The system shall keep configured advanced search
  criteria visibly reflected in the search form before submission.” Both named
  criteria remain visible in the required pre-submission state.
- `REQ-12` — `PARTIALLY_FULFILLED`: “The system shall carry active advanced
  search filters forward into subsequent browsing views so users can understand
  the basis of the shown results.” The same form state supports the active-filter
  part, but no later browsing or results view is recorded.

The second item is not an abstention because an important part of its actual
obligation—the active filters—is visibly supported. It is not fulfilled because
its temporal scope extends beyond the recorded form state.

### 5.7 Missing, Hidden, and Contradicted: Carnival Search

Three requirements over the Carnival cruise-search flow illustrate why the
absence of positive evidence does not always imply the same label:
They were selected during later author review as supplementary calibration
examples, not as part of the prespecified RQ3 case set.

- `REQ-13` — `PARTIALLY_FULFILLED`: The requirement asks the system to return
  cruise results reflecting destination, departure port, month, and duration.
  Step 9 shows all four configured criteria and the submission control, but not
  the returned results. One core part is supported and the result outcome is
  missing.
- `REQ-14` — `ABSTAIN`: The requirement allows only itinerary options that are
  genuinely searchable or available. The flow shows option values, but their
  genuine availability depends on hidden inventory and searchability logic.
  Visible option presentation is only supporting context for the unresolved
  core property.
- `CONTR-05` — `NOT_FULFILLED`: The requirement demands a dedicated pre-search
  review step or summary panel that lists all criteria and permits editing.
  Steps 1–9 expose the complete pre-submission sequence: criteria remain
  editable in the ordinary search form, but the required dedicated review stage
  is absent. Here the observed sequence provides counter-evidence rather than
  merely stopping too early.

The three labels follow from the relation between the requirement and the
recorded evidence: supported core plus missing outcome yields partial
fulfillment; a hidden core property yields abstention; and a visible completed
sequence incompatible with a required component yields non-fulfillment. This
distinction was one of the main judgment problems during author review.

### 5.8 PURE as Exploratory External Material

PURE is a corpus of public requirements documents collected from heterogeneous sources and formats (Ferrari, Spagnolo, and Gnesi, 2017). Its documents are useful because their requirements are not generated from the screenshot trajectories used in the main benchmark. The selected documents examined here contain longer, more formal requirements and cases that depend on headings, surrounding paragraphs, figures, or system context.

This material offers a closer approximation to requirements encountered in
requirements-first practice than requirements reconstructed from completed UI
flows. However, PURE was not designed for screenshot-based verification. Most
source requirements are not accompanied by an aligned screenshot sequence, and
the available figures often expose only a static or partial state. The accepted
subset is therefore a curated set of requirements that could be meaningfully
associated with visual material, not a representative sample of screenshot
coverage across the source documents.

The pipeline first extracts selected PURE requirements deterministically and
then uses AI assistance to contextualize fragments that are not self-contained.
It associates the resulting candidates with UI images from the documents. The
Split/Merge subset contains 31 accepted verification items and 78 claims, while
Mashboot contains 11 accepted items. Across both subsets, 25 items are
fulfilled, nine are partially fulfilled, and eight require abstention. Every
accepted formulation, label, claim set, and evidence link received
primary-author review independently of the evaluated model predictions. The
longer and often compound PURE requirements also motivated the claim
decomposition stage used in the main approach.

PURE can support qualitative discussion about context dependence, compound
requirements, and UI verifiability. The analysis treats the associated UI
images as document artifacts and reports document-to-UI consistency separately
from implementation conformance over recorded execution flows.

One Split/Merge item illustrates the difference. Its requirement specifies
exactly two input PDF documents. Step 5 shows one configuration with two
documents, while step 23 shows the empty input table and its add and remove
controls. This supports the intended two-document workflow but does not show
whether the application rejects one or three inputs. The accepted label is
therefore `PARTIALLY_FULFILLED`, not `FULFILLED`.

### 5.9 Review Workflow and Quality Controls

Review occurs at the candidate and verification stages. Candidate review checks
whether the text forms a meaningful, self-contained requirement for the
intended application context. Verification review checks UI evaluability,
label, claims, evidence steps, uncertainty reasons, and rationale against the
ordered flow.

The workbench validates structural constraints. A fulfilled item requires
evidence and may not contain a contradicted core claim. A negative item requires
visible counter-evidence. A partial item requires supported and unresolved
material content. An abstention requires an insufficiency reason. These checks
identify internally inconsistent records, but they cannot decide whether the
reviewer's interpretation of the screenshots is correct.

All 258 Mind2Web items and all accepted PURE items received manual
primary-author review independently of the evaluated model predictions. The
repository records review status and annotation provenance so that
candidate-generation assistance remains distinct from human reference
decisions. The completed primary-author decisions form the reference set used
in the reported evaluation.

UI-evaluability and region-grounding reviews use their own targeted samples.
Separate review tasks preserve differences between fulfillment, UI
evaluability, screenshot selection, and region sufficiency. Agreement at one
level does not establish agreement at another.

### 5.10 Benchmark Characteristics

The benchmark is organized by flow. Items
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
the gold files. Evaluation reports missing predictions explicitly and never
treats them as abstentions.

### 5.11 Data Governance

The 13 Mind2Web flows belong to the separately distributed `test_task` split.
Original screenshots, HTML, traces, videos, and unzipped test records remain
local. The repository can recreate the working flow set from identifiers after
the user obtains Mind2Web through the official source, but it does not mirror
the underlying test archive.

PURE 2.0 is obtained from Zenodo under CC BY 4.0 [@purezenodo2018]. Reviewed
annotations and aggregate results are published with attribution and a change
notice. Because the curators did not verify the rights of every collected Web
document, the release retains their provenance and takedown caveat. Original
archives are installed directly from Zenodo rather than duplicated. Section 7.7
discusses the implications for reproducibility.

## 6 Evaluation

### 6.1 Evaluation Design

#### Compared Systems

The primary experiment covers all 258 verification items from flows 01–13.
Its central comparison is a two-by-two Gemini 3.1 Flash-Lite matrix in which
claim policy and screenshot policy are varied independently. The raw policy
treats each requirement as one unit, while gated decomposition splits selected
compound requirements. The all-screenshot policy supplies the complete flow,
while shared top-4 supplies a batch-level set of four screenshots derived from
lexical item-level candidates. All
other recorded settings are held constant.

RQ1 additionally uses a matched Gemini 2.5 Flash-Lite raw/all run and a hosted
Qwen3-VL-8B-Instruct raw/top-4 run. Here, top-4 denotes only the deterministic
evidence-selection policy; Qwen remains the multimodal LLM verifier. The separate
deterministic raw/top-4 and gated/top-4 configurations use no model and provide
non-LLM reference points. Historical Gemini
3.1 Pro and provided-claim runs remain useful sensitivity and oracle analyses,
but they are not inserted into the controlled matrix because their prompt,
claim, grouping, or grounding settings differ.

All headline comparisons require complete 258-item coverage. Missing model
outputs are counted as coverage failures and listed separately; they are not
converted to `ABSTAIN`. Exact model identifiers, dates, prompt versions,
generation parameters, image preparation, call counts, tokens, cost, failures,
fallbacks, and repository hashes are attached to the frozen run manifests.

Earlier 201-item runs were used during development, but they are not reported
as thesis results because the controlled 258-item benchmark supersedes them.
Historical predictions are kept only as provenance artifacts and are never
mixed with the final reference set.

#### Label Metrics

Accuracy is the fraction of verification items whose predicted label equals the gold label. It is intuitive but insufficient under the current class distribution. A system that predicts `FULFILLED` for every item would already be correct on 66.7% of the full 258-item snapshot.

Macro-F1 calculates an F1 score independently for each of the four labels and averages them with equal weight. It therefore penalizes failure on `PARTIALLY_FULFILLED`, `NOT_FULFILLED`, or `ABSTAIN` even when those labels are uncommon. Weighted-F1 may be included as a secondary summary but inherits the influence of the majority class.

The false-fulfillment rate is defined as the fraction of predicted `FULFILLED` items whose gold label is not `FULFILLED`. This is a precision-oriented safety metric. It answers: when the system makes its strongest positive claim, how often is that claim too strong? The numerator includes gold partial, negative, and abstaining cases. The metric must be interpreted together with the number of predicted fulfilled items; a system could trivially reduce it by never predicting `FULFILLED`.

The abstain rate is the fraction of all predictions labeled `ABSTAIN`. Prediction coverage records the fraction of gold items for which an explicit model prediction exists. Missing predictions are not equivalent to model abstentions and must be reported separately. All configurations in the final controlled matrix have complete prediction coverage.

#### Evidence Metrics

Evidence evaluation compares the predicted screenshot steps with the reviewed
evidence steps. Hit@k is one if at least one reviewed step occurs in the first
k returned steps and zero otherwise, averaged over items. Recall@k measures the
fraction of reviewed steps covered within that prefix, while precision@k
measures how many returned steps belong to the reference set. The evaluator
also records the reciprocal position of the first relevant step. Because
requirement-level evidence is normalized into chronological step order, its
mean is reported as chronological reciprocal rank (chronological RR), not as a
confidence-ranked retrieval measure.

These metrics capture different properties. A high hit@1 indicates that the
earliest returned evidence step often matches the reviewed trace. It does not
show that all evidence required for a multi-step claim was returned. Recall is
important when an action and its result occur on different screens or when a
requirement contains several obligations. Evidence overlap also cannot
determine whether the model interpreted the screenshot correctly; it measures
trace alignment rather than semantic reasoning.

The 258-item evaluators normalize screenshot-step evidence across the current
model configurations. Every reported evidence value therefore names its run
and uses the same benchmark denominator.

#### Claim Metrics and Qualitative Analysis

When predicted claims are available, they are matched to gold claims using text similarity before claim statuses are compared. Claim-match recall reports how many gold claims receive an acceptable predicted match. Claim-status macro-F1 then evaluates the status of matched claims. These metrics are sensitive to decomposition quality: a semantically valid split may use different wording or granularity from the gold annotation. Claim evaluation should therefore combine automatic matching with a manually inspected sample.

Qualitative error analysis assigns errors to recurring categories rather than treating them as unrelated mistakes. The main categories are over-fulfillment, anti-abstention, under-calling caused by missed evidence, and label-boundary disagreements. The analysis also records semantic patterns such as universal quantifiers, comparisons, result correctness, persistence, hidden system properties, and late cart or summary states.

#### Statistical Comparison and Run Stability

The primary comparisons are paired because every configuration predicts the
same requirements from the same flows. To preserve the dependence among items
within an application flow, uncertainty intervals are generated with a cluster
bootstrap that resamples the 13 complete flows with replacement
[@fieldwelsh2007]. Each bootstrap replicate reconstructs
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
accuracy, macro-F1, false fulfillment, and chronological RR show whether headline
conclusions change. Repetitions are not additional test samples and are not
pooled to inflate the denominator.

The order-unavailable comparison is paired in the same way. In addition to the
full benchmark, it reports the 194 multi-screen items, the 175 items with
multi-step gold evidence, the 64 single-screen items as a negative control, and
a frozen 59-item lexical subset containing sequence-related formulations such as
preservation, updates, result states, confirmation, cart, or checkout. Because
this subset is heuristic and the benchmark has only 13 flows, subgroup
differences are treated as diagnostics rather than population-level effects.

### 6.2 RQ1: Model Performance

The matched raw/all comparison provides the main model-sensitivity result.
Gemini 3.1 Flash-Lite reaches 79.5% accuracy and 0.511 macro-F1, compared with
73.3% and 0.413 for Gemini 2.5 Flash-Lite. A paired flow-cluster bootstrap
estimates an accuracy difference of 6.2 percentage points with a 95% interval
from 1.6 to 10.8. The models assign the same label to 83.3% of items, with
Cohen's kappa of 0.616.

Within the primary raw/all condition, accuracy is 88.8% (166/187) for source
requirements and 54.9% (39/71) for contrastive requirements. Among `FULFILLED`
predictions, false fulfillment is 5.3% (9/170) and 57.9% (11/19), respectively.
Because provenance, label distributions, and visible identifiers differ, this
split is descriptive rather than a causal comparison.

Under the shared raw/top-4 condition, Gemini 3.1 Flash-Lite and
Qwen3-VL-8B-Instruct both reach 71.3% accuracy and nearly identical
chronological RR. Their error profiles differ: Qwen has a false-fulfillment rate of 18.5%,
7.4 percentage points above Flash-Lite, and a lower macro-F1 of 0.356. The
equal headline accuracy therefore does not imply equivalent verification
behavior.

### 6.3 RQ2: Claim Decomposition and Screenshot Selection

The primary RQ2 matrix uses the same 258 accepted items from flows 01–13,
Gemini 3.1 Flash-Lite, prompt version, label schema, aggregation, and execution
parameters in every cell. Only claim policy and screenshot policy vary. All
four cells have complete prediction coverage and no recorded fallback or
failure.

\begin{table}[htbp]
  \centering
  \small
  \setlength{\tabcolsep}{4.2pt}
  \begin{tabular}{@{}llrrrrrr@{}}
    \toprule
    \textbf{Claims} & \textbf{Screenshots} & \textbf{Acc.} & \textbf{Macro-F1} &
    \textbf{FF rate} & \textbf{Abstain} & \textbf{Chron. RR} & \textbf{Cost} \\
    \midrule
    Raw & All & 0.795 & 0.511 & 0.106 & 0.190 & 0.716 & \$0.2817 \\
    Gated & All & 0.791 & 0.532 & 0.124 & 0.171 & 0.734 & \$0.3002 \\
    Raw & Shared top-4 & 0.713 & 0.387 & 0.110 & 0.279 & 0.621 & \$0.2778 \\
    Gated & Shared top-4 & 0.736 & 0.511 & 0.104 & 0.260 & 0.607 & \$0.2394 \\
    \bottomrule
  \end{tabular}
  \caption{Controlled Gemini 3.1 Flash-Lite comparison over 258 requirements in
  13 flows. FF rate denotes false fulfillment; cost is the recorded estimated
  API cost. Chron. RR is the mean reciprocal position of the first matching
  step in the chronologically ordered returned trace.}
  \label{tab:controlled-full-benchmark}
\end{table}

The table shows the interaction without a separate chart: decomposition changes
little with all screenshots, whereas it partly recovers the loss caused by
shared top-4 selection.

A paired 10,000-sample percentile bootstrap over the 13 flows gives a 95%
interval of -12.0 to -3.8 percentage points for raw shared-top-4 versus raw/all
accuracy difference and -0.226 to -0.043 for macro-F1. The chronological-RR difference is
also below zero. Restricting each batch to four shared screenshots loses
measurable information while reducing estimated cost by less than half a cent.
Repeated screenshots across batches and output and thinking tokens offset much
of the lower image input.

Automatic gated decomposition does not consistently improve accuracy, false
fulfillment, or chronological evidence-trace alignment. With all screenshots,
its accuracy and macro-F1 difference intervals span zero, while false
fulfillment increases by 1.9 percentage points with a 95% interval from +0.4
to +3.3. Under top-4 evidence, decomposition improves macro-F1 by 0.123 with an
interval from +0.021 to +0.183, suggesting an interaction between requirement
granularity and restricted evidence. With only 13 resampled clusters, these
intervals must still be interpreted cautiously.

An offline policy counterfactual replaced every native `ABSTAIN` with `NOT_FULFILLED` without making new model calls. Accuracy fell from 0.795 to 0.702 for raw/all and from 0.736 to 0.643 for gated/top-4; macro-F1 fell to 0.332 and 0.306. False fulfillment was unchanged because the policy cannot generate a positive label. The result shows that treating absence of sufficient evidence as a negative verdict is harmful on this benchmark. It does not show that every abstention is calibrated or that abstention causally reduces unsafe positive predictions.

### 6.4 Robustness and Run-to-Run Stability

Two independent repetitions were executed for the raw/all and gated/top-4
Gemini anchors and for the hosted Qwen raw/shared-top-4 baseline. Every
repetition covered all 13 flows and 258 items. The new Gemini runs used 160
first-attempt API calls without cache hits, fallbacks, or failures; the Qwen
runs used 78 first-attempt calls, were served by Alibaba with provider fallbacks
disabled, and likewise recorded no failures.

Gemini produced exactly the same requirement label for every item in all three
executions of both configurations. Raw/all therefore remains at 0.795 accuracy
and 0.511 macro-F1 in every run, while gated/top-4 remains at 0.736 accuracy and
0.511 macro-F1. Screenshot-step evidence was not perfectly invariant: raw/all
chronological RR ranges from 0.712 to 0.716 and gated/top-4 from 0.607 to 0.610.

Qwen shows small but measurable variation. Across three executions, accuracy
ranges from 0.705 to 0.713, macro-F1 from 0.345 to 0.356, false fulfillment from
0.185 to 0.189, and chronological RR from 0.622 to 0.635. Pairwise label agreement
ranges from 0.965 to 0.988, with Cohen's kappa between 0.906 and 0.969. These
figures indicate strong descriptive stability without implying determinism or
treating repeated executions on the same benchmark as independent samples.

The six repetitions cost approximately USD 1.1245 in recorded successful
inference usage. Bounding boxes were not requested in the Qwen runs. The Gemini
prompt did produce unvalidated free-form visual regions, but the mature
evaluated evidence contribution remains screenshot-step traceability.

#### Order-Unavailable Robustness Result

The chronology-destroying condition completed all 13 flows and 258 items with
39 successful API calls, no fallback, and no recorded failure. It used 622,225
tokens and cost an estimated USD 0.2847. Against the corrected frozen
reference, the matched ordered condition reaches 79.5% accuracy, 0.511 macro-F1,
19.0% abstention, 10.6% false fulfillment, and 0.716 chronological RR. When
trustworthy order is removed, accuracy falls to 74.8%, macro-F1 to 0.425, and
chronological RR to 0.665, while abstention rises to 24.8%. False fulfillment is
11.2%.

The paired difference in accuracy is -4.7 percentage points. A 10,000-sample
percentile bootstrap over complete flows gives a descriptive 95% interval from
-7.3 to -2.0 percentage points. The abstention difference is +5.8 points, with
an interval from +1.6 to +10.4. The chronological-RR interval spans zero. Overall,
28 of 258 labels change. Fourteen change from `FULFILLED` to `ABSTAIN`; the
remaining flips include changes in both conservative and less conservative
directions, so the result does not establish that withholding chronology
uniformly improves safety.

The label-flip rate is 18.6% in the frozen 59-item sequence-sensitive lexical
subset, 12.4% across all multi-screen items, and 6.3% in the single-screen
negative control. The sequence-sensitive accuracy difference is -6.8 points,
but its flow-cluster interval spans zero. The results therefore show that
removing trustworthy order materially changes model decisions and reduces
aggregate label performance on this benchmark. They do not isolate a stable
effect for every temporal requirement category, and part of the change may
reflect the model's response to the explicit instruction that chronology is
unavailable.

### 6.5 RQ3: Screenshot-Aware Error Analysis

#### RQ3 Error-Analysis Protocol

The RQ3 analysis uses frozen predictions. Each incorrect prediction receives
exactly one primary error category and may receive multiple requirement- and
evidence-pattern tags. Abstentions are coded separately so that a justified
hidden-outcome abstention is not grouped with a retrieval failure.

Model-error categories include unsafe over-fulfillment, unsupported concrete
negatives, excessive abstention, evidence-interpretation errors, and
label-boundary disagreements. Evidence errors distinguish selection misses from
traceability failures. Requirement-pattern tags cover quantifiers, comparisons,
persistence, external effects, late results, multi-screen composition, and
ambiguous scope.

The categories were produced through LLM-assisted visual coding with targeted
primary-author review; they are descriptive and do not constitute independent
human adjudication.

The following table reports only mechanically observable triggers that can be
derived without causal judgment. Errors and abstentions use 258 as their
denominator; the false-fulfillment rate uses predicted `FULFILLED` decisions.
“Trace miss” counts correct labels whose cited steps have no overlap with
reviewed evidence. “Input gap” counts items for which the supplied screenshots
omit at least one reviewed evidence step. These columns are mechanical triggers,
not mutually exclusive error categories.

\begin{table}[htbp]
  \centering
  \small
  \begin{tabular}{@{}lrrr@{\hspace{1.25em}}rrr@{}}
    \toprule
    Config. & Errors & Abst. & Unsafe F & FF rate & Trace miss & Input gap \\
    \midrule
    FL r/all   & 53 & 49 & 20 & 10.6\% & 41 & 0 \\
    FL g/all   & 54 & 44 & 24 & 12.4\% & 41 & 0 \\
    FL r/t4    & 74 & 72 & 19 & 11.0\% & 43 & 135 \\
    FL g/t4    & 68 & 67 & 18 & 10.4\% & 51 & 138 \\
    G25 r/all  & 69 & 57 & 25 & 13.7\% & 34 & 0 \\
    Qwen r/t4  & 74 & 60 & 36 & 18.5\% & 49 & 135 \\
    \bottomrule
  \end{tabular}
  \caption{Automatic RQ3 trigger inventory over 258 requirements. FL denotes
  Gemini 3.1 Flash-Lite, G25 Gemini 2.5 Flash-Lite, r raw requirements, g gated
  decomposition, and t4 lexical top-4 input. Counts overlap because the columns
  test separate properties of the same items; for example, an error may also be
  an abstention or unsafe fulfillment, and an input gap may coexist with either.
  They are mechanical triggers, not manually coded causes.}
  \label{tab:rq3-trigger-inventory}
\end{table}
\FloatBarrier

The completed audit contains 653 condition–item rows from 153 distinct
requirements. Of these, 392 have a prediction different from the accepted
reference. Table \ref{tab:rq3-visual-error-categories} reports exactly one
primary category for each of these label errors. It does not treat repeated
conditions as independent benchmark items.

\begin{table}[htbp]
  \centering
  \small
  \begin{tabular}{@{}lrrr@{}}
    \toprule
    Primary category & Count & Share of 392 errors & Distinct reqs. \\
    \midrule
    Unsafe over-fulfillment       & 142 & 36.2\% & 51 \\
    Excessive abstention          & 138 & 35.2\% & 47 \\
    Evidence-selection miss       &  57 & 14.5\% & 29 \\
    Evidence-interpretation error &  35 &  8.9\% & 16 \\
    Label-boundary disagreement   &  12 &  3.1\% &  3 \\
    Unsupported concrete negative &   8 &  2.0\% &  4 \\
    \bottomrule
  \end{tabular}
  \caption{Screenshot-aware primary categories among the 392 condition--item
  rows with a label error. Distinct-requirement counts may overlap across
  categories when conditions fail differently. The rows originate from six
  conditions over the same benchmark and are descriptive rather than
  independent prevalence samples.}
  \label{tab:rq3-visual-error-categories}
\end{table}
\FloatBarrier

The largest category is unsafe over-fulfillment. In all 142 cases, the verifier
predicts `FULFILLED` although the accepted label is lower. Excessive abstention
accounts for a further 138 errors: decisive evidence is available in the
supplied screenshots, but the verifier still abstains. Selection misses are
concentrated in the top-4 conditions. They account for 24 of 74 errors in the raw
top-4 run, 21 of 68 in the gated top-4 run, and 12 of 74 in the Qwen top-4 run,
but none of the label errors in the three complete-flow conditions. This
separation supports the distinction between retrieval failure and reasoning
failure.

The 349 model abstentions also contain correct conservative decisions. Of these,
153 (43.8%) are appropriate abstentions, 138 (39.5%) are excessive, 47 (13.5%)
follow an evidence-selection miss, and 11 (3.2%) reflect the adopted label
boundary. Abstention is therefore neither uniformly desirable nor uniformly
erroneous. A correct non-abstaining label can still have a defective trace.
After screenshot inspection, 92 additional selected rows were coded as
traceability failures because the cited evidence was incorrect or did not
support the decision. Zero overlap with the non-exhaustive reviewed evidence
set was only a mechanical review trigger and was not sufficient for this
judgment.

The multi-valued requirement tags describe where errors occur rather than
forming exclusive causes. Multi-screen composition appears in 202 of 392 label
errors (51.5%), late result or cart state in 125 (31.9%), hidden backend or
external behavior in 123 (31.4%), persistence across steps in 108 (27.6%),
universal or completeness wording in 72 (18.4%), and comparative wording in 53
(13.5%). At evidence level, partial claim coverage appears in 248 errors
(63.3%), while 91 (23.2%) expose only an entry point and 59 (15.1%) show an
action without its result. These overlapping tags support the qualitative
mechanisms described above but do not identify independent causal effects.

RQ3 is therefore answered descriptively for the frozen benchmark: the dominant
failures are over-claiming full support, abstaining despite supplied evidence,
and losing decisive screenshots under restricted selection. These outcomes are
associated most often with multi-screen, late-state, hidden, persistent, and
partially visible obligations. The 13-flow design and LLM-assisted coding do not
support population-level prevalence or independent-human reliability claims.

#### RQ3 Error Mechanisms and Illustrative Cases

The following mechanisms characterize the final error categories. The automatic
trigger inventory measures review workload, not causal frequency.

Over-fulfillment occurs when the verifier treats a visible entry point as
evidence for the complete requirement. A search form becomes proof of correct
results, a link becomes proof of applicability, or one observed path becomes
proof of a universal condition. These cases directly increase false
fulfillment.

Hidden and external outcomes include persistence, availability, delivery,
payment, security, and backend correctness. The screenshots usually show only a
UI proxy. Models still infer concrete outcomes in some cases; central hidden
obligations should retain `HIDDEN` or `AMBIGUOUS` status.

Universal and comparative language is a cross-cutting requirement pattern, not
an additional primary error category. Terms such as “all,” “every,” “only,” and
“always” raise the required evidence scope, while a flow often contains only
one instance. Comparisons require both sides or a visible invariant across the
relevant states. The model often generalizes beyond the recorded example.

Missing late states affect cart, checkout, result, review, and summary
requirements. Lexical overlap favors earlier screens that contain the
requirement vocabulary and can omit a later outcome state.

Boundary disagreements occur mainly between `PARTIALLY_FULFILLED` and
`ABSTAIN`, and between `NOT_FULFILLED` and `ABSTAIN`. Under the adopted policy,
the negative label requires visible contradiction. An omitted result state
supports abstention; a supported entry point followed by an unobserved result
can support partial fulfillment. The annotation guide records examples for
consistent author re-inspection.

The Book Depository pair in Section 5.6 isolates the partial-versus-abstain
boundary. All four controlled Gemini 3.1 Flash-Lite conditions and the Gemini
2.5 baseline correctly fulfilled the requirement limited to the current form,
but abstained on the requirement extending the same filters into later views.
They therefore discarded visible support that the gold annotation retains for
a partial label. The primary Qwen run made the opposite error and fulfilled
both requirements, extending current-form evidence into an unobserved later
state.

The Carnival cases in Section 5.7 expose the same calibration problem across
three labels. Every reported primary condition abstained on `REQ-13`, although
the visible combined query supports a partial label. The final consistency
review therefore classifies these six abstentions as excessive rather than as
boundary disagreements. The five Gemini conditions
correctly abstained on the hidden availability claim in `REQ-14`, while Qwen
inferred fulfillment from the displayed options. Only gated/top-4 recovered
`NOT_FULFILLED` for the visibly absent dedicated review stage in `CONTR-05`;
the other primary conditions softened the case to partial fulfillment or
abstention. These paired outcomes show that the errors are not captured by a
single tendency toward optimism or conservatism.

#### Late-State Failure Example

The Six Flags purchase flow (flow 10) provides a representative selection miss.
Requirements about quantities, fees, totals, and cart modification depend on
the final cart state in steps 8--10, while lexical selection often retained
earlier configuration screens. Without the late summary, the verifier cannot
support these decisions even though the complete flow contains the evidence.
This case motivates action/result pairing, late-state priorities, and a fallback
to the complete flow. Longer flows still increase image tokens and irrelevant
content, so retrieval remains a trade-off rather than an inherent improvement.

### 6.6 Auxiliary UI-Evaluability Results

#### Method

UI evaluability is evaluated separately from fulfillment. The first analysis
compares the evaluability predicted in the realistic raw-requirement run with
the reviewed three-class labels. Because the class distribution is highly
imbalanced, raw agreement is accompanied by macro-F1, balanced accuracy,
per-class recall, unweighted Cohen's kappa, and ordinal-weighted kappa.

A deterministic text classifier tests whether simple lexical rules capture the
visible/hidden boundary at low cost. Majority-class accuracy is insufficient
when partially and non-verifiable requirements are missed.

The completed diagnostic contains all 81 disagreements between the original
stored labels and the deterministic classifier across 300 accepted Mind2Web and
PURE items. The author retained 51 references, adopted 27 classifier labels,
and chose a different label in three cases. The resulting 30 amendments update
the stored UI-evaluability records before the auxiliary multimodal result is
calculated. Because the items were disagreement-selected and the classifier
output was visible, the review improves reference consistency but cannot yield
an unbiased estimate of that classifier's accuracy. Mind2Web and PURE remain
separate, and the three `NOT_UI_VERIFIABLE` items in the main benchmark are too
few for a stable class-specific estimate.

The realistic raw-requirement run predicts UI evaluability without receiving
the gold value in the prompt. On the 258 Mind2Web verification items, its raw
agreement with the current labels is 89.1%, macro-F1 is 0.504, unweighted
Cohen's kappa is 0.521, and ordinal-weighted kappa is 0.529. The aggregate
agreement is dominated by `UI_VERIFIABLE`: recall is 96.8% for this class,
48.6% for `PARTIALLY_UI_VERIFIABLE`, and 0% for the three
`NOT_UI_VERIFIABLE` items.

The result reveals a systematic tendency to treat a visible interface core as
evidence that the entire requirement is UI-verifiable. Requirements combining
visible interaction with persistence, completeness, external delivery, policy,
or backend correctness are consequently collapsed into the majority class.
This is relevant to RQ3 because the same hidden obligations can later produce
over-fulfillment or unstable boundaries between partial fulfillment and
abstention.

The deterministic text baseline illustrates the effect of class imbalance.
On the broader 300-item accepted snapshot it reaches 72.7% accuracy but only
0.373 balanced accuracy, 0.322 macro-F1, and 0.010 Cohen's kappa. It predicts
the majority class for 284 items and does not correctly recover the
`PARTIALLY_UI_VERIFIABLE` class. Simple keyword rules are therefore
insufficient for the current three-way construct.

The resulting multimodal agreement remains auxiliary because the benchmark has
only three `NOT_UI_VERIFIABLE` items and the later reference review was neither
blind nor independent of automated diagnostic information. The deterministic
classifier therefore describes majority-class behavior rather than an unbiased
post-amendment accuracy estimate. PURE remains separate from the 258-item
Mind2Web result.

### 6.7 Auxiliary Region-Grounding Findings

#### Method

Region grounding is scoped as a traceability output, not as an intervention on
label accuracy. A frozen 60-item author audit samples four returned-region
claims per flow and includes all eight explicit no-region outputs from the V7
run. It records whether a claim needs one region, several regions, a whole
screen or transition, or no visible region, and separately assesses geometric
validity, semantic relevance, evidential sufficiency, proposal availability,
and localization abstention. This targeted single-author sample supports a
diagnostic result, not a benchmark-wide grounding estimate and not an answer to
RQ1--RQ3.

The system can produce and display claim-specific evidence regions and can
explicitly return `NO_VISIBLE_REGION`. Implementation coverage is not a quality
metric, however: an early focused OCR inspection marked 13 of 14 proposals
incorrect, usually because a nearby keyword was selected instead of the value,
control, or state that supported the claim. This motivated the frozen audit of
the later proposal-based method.

The frozen V7 audit contains 60 completed author reviews. Of the 52 items with
returned regions, 45 have valid geometry and seven have invalid geometry. The
regions are relevant in 39 cases, partially relevant in nine, and irrelevant in
four. They are sufficient for the claim in 21 cases, partially sufficient in
23, and insufficient in eight. The remaining eight items are explicit
no-region outputs and are not assigned region geometry, relevance, or
sufficiency scores.

The applicability review also shows why a single-box metric would be
misleading: 29 claims require multiple regions, 14 one region, 15 a whole-screen
state or transition, and two no visible region. Among the eight explicit
no-region outputs, seven localization abstentions are appropriate and one is
not. These figures characterize the
targeted sample only. Reviews from earlier methods are not pooled because their
candidate generators, prompts, resolutions, flows, and inspection procedures
differ.

A focused GameStop diagnostic further showed that proposal coverage matters:
extending OCR to the lower page exposed the decisive address regions shown in
Figure \ref{fig:gamestop-quantifier-counterexample}.

## 7 Discussion and Threats to Validity

### 7.1 Interpretation and Practical Implications

Adding pipeline stages does not consistently improve verification. Raw
requirements with all screenshots produce the highest accuracy in the primary
Flash-Lite matrix. Shared lexical top-4 omits decisive information and saves almost no
money under the implemented batching strategy. Automatic decomposition
improves macro-F1 under restricted evidence, but all-screenshot accuracy remains
unchanged and false fulfillment increases. Requirement understanding and
screenshot selection consequently need separate evaluation.

The evidence-first representation primarily improves inspectability. It records
selected screenshots, supported and unresolved claims, uncertainty reasons, and
localized evidence. A reviewer can then separate retrieval errors from visual
interpretation and label-policy disagreements. Direct whole-flow prompting and
staged verification can therefore differ in label quality and diagnostic
detail.

This diagnostic structure also suggests a practical improvement cycle. Errors
can first be assigned to the frozen primary categories and then inspected for
recurring mechanisms. Over-fulfillment and boundary errors can motivate clearer
evidence-sufficiency rules; excessive abstention can reveal when visible partial
support should be retained; and selection misses can guide evidence acquisition.
The resulting general rules can be added to the label guide, prompt, or
deterministic gates and evaluated again on held-out flows. Repeating this cycle
turns the taxonomy into a development tool rather than only a reporting device.

Iterative correction can also shift rather than eliminate errors. In the current
setting, a rule designed to retain more visible partial support might reduce
excessive abstention while weakening the evidential threshold and increasing
over-fulfillment. Such refinement is plausible only if the multimodal model can
apply the added rules and interpret the relevant UI states. The present results
show that many errors follow recurring policies rather than isolated output
failures, but they do not establish that prompt refinement will remove them or
that visual understanding is sufficient beyond the predominantly web-based
benchmark. Each iteration must therefore retain abstention, monitor error
trade-offs, and be tested on new applications instead of the examples used to
derive the rules.

For a practical deployment, the results favor an adaptive rather than fixed
retrieval policy. Complete flows are appropriate while flows remain short
enough for the model context and budget. Retrieval becomes useful when flows
grow, but it should monitor evidence sufficiency and fall back to additional
screens when outcome states, transitions, or multiple obligations are
unresolved. Late-screen priors and action/result pairing are concrete
improvements suggested by the observed failures.

The evidential threshold for fulfillment is context-dependent. A
safety-critical setting may prefer more abstention, while another project may
classify missing required evidence as failure. In this study, the four label
definitions are fixed across all applications and flows, supplied to the model,
enforced by the aggregator, and evaluated with safety-oriented metrics. Other
risk policies can be compared by changing these explicit rules instead of
folding them into a binary score.

### 7.2 Internal Validity

All current Mind2Web verification items were reviewed by the primary author
independently of the evaluated model predictions. The documented reference
standard includes requirement labels, claim boundaries, evidence sets, and
UI-evaluability judgments. Reported model metrics quantify agreement with this
reviewed reference standard. The separately prompted multimodal UI-evaluability
result is therefore reported as auxiliary evidence rather than a central RQ
result.

The requirements are derived from the same flows against which they are
evaluated. Prediction-independent manual review keeps evaluated outputs
separate from reference decisions. Separate reporting for original and
contrastive requirements, flow-level resampling, and the exploratory PURE
document comparison make the construction and evidence sources visible in the
analysis.

The verifier input excludes intended and accepted labels, but it includes the
requirement identifier. All contrastive items use a `CONTR-` prefix, so the
model can infer construction provenance even though it cannot infer the target
label from that prefix. The experiment is target-label-blind but not
provenance-blind. This cue may contribute to the source--contrastive difference,
which is why that comparison is descriptive rather than a causal estimate of
difficulty.

Model outputs are sensitive to model version, prompt text, image preparation,
retries, and aggregation. The final comparisons are tied to stored prediction
files, input hashes, exact model identifiers, and run metadata. Some first
executions were made from a recorded commit with a dirty worktree; later
stability runs used clean manifests. This limits byte-for-byte reconstruction
of those first calls, but stored outputs can still be rescored against the
matching frozen reference.

### 7.3 Construct Validity

The four labels operationalize a conservative interpretation of screenshot-based verification. Other projects might define missing evidence as failure or treat visible success messages as sufficient proof of a backend outcome. The adopted label policy is therefore a deliberate construct tied to the intended safety goal rather than the only possible definition.

The label definitions specify the meaning of the four verdicts, but they do not
fully specify when visible evidence is sufficient for assigning them. When a
control, message, or interface state suggests the required behavior, the
verifier must decide whether that cue establishes the behavior or merely makes
it plausible. With only generic evidence guidance, part of this decision is
supplied by the model's implicit assumptions. The observed cross-model
disagreements are consistent with such model-dependent interpretation, even
though repeated executions of the same Gemini configuration produced stable
labels. The study retained one generic evidence policy because the 13-flow
benchmark was too narrow to derive detailed sufficiency criteria without
risking calibration to its particular applications and items.

Screenshot-step overlap is an incomplete measure of evidence quality. Human annotations may contain several valid screens, and a prediction may cite a semantically valid alternative that is absent from the reference set. Conversely, retrieving a gold step does not prove that the model used the correct region or interpretation. Manual evidence inspection should complement the automated metrics.

Region-level review introduces a related construct question. A visually tight
box is not necessarily the most useful explanation, and some claims require a
whole-screen state, multiple regions, or a transition. The grounding evaluation
therefore combines geometric measures with human relevance and sufficiency
judgments instead of defining correctness only through intersection over union.

UI evaluability is also a constructed boundary. The difference between a
routine hidden dependency behind a visible success proxy and a nontrivial
hidden property can depend on the application risk model. This boundary
therefore requires the same explicit evidence guidance as the fulfillment
labels.

Claim matching introduces additional uncertainty. Two decompositions can be
semantically equivalent while using different granularity. Low claim-status
performance may reflect a poor decomposition, poor text matching, or poor
status prediction. Where claim metrics are reported, claim-match recall is
therefore kept separate from status quality on matched claims.

### 7.4 External Validity

Thirteen web flows are a small sample of the variety of real interfaces and requirements. The selected tasks do not establish generalization to native mobile applications, desktop software, accessibility requirements, or industrial specifications. Mind2Web trajectories reflect one recorded interaction path and may omit alternative states relevant to a requirement.

An error-driven refinement cycle would intensify this limitation if rules were
derived and evaluated on the same flows. Because the benchmark is dominated by
web UI trajectories and requirements reconstructed from them, repeated tuning
could overfit both its interface type and its evidence patterns. Development
examples, validation flows, and a held-out test set should therefore be
separated. The test set should include native mobile and desktop interfaces as
well as independently authored requirements drawn from real projects, so that
apparent improvements are not benchmark-specific prompt tuning.

The primary benchmark also reverses the usual requirements-first development
order. Its source requirements were reconstructed from already observed web
flows, so the contract and its evidence are not independent. This construction
supports controlled evaluation of evidence interpretation, but it favors
requirements that align with established interface behavior and does not
reproduce a setting in which an independently authored requirement precedes a
design or implementation that may violate it. The study neither generated UI
drafts nor seeded implementation defects. Contrastive items introduce
unsupported and contradictory cases, but they are constructed deviations
rather than observed implementation defects. The results therefore do not
estimate defect-detection performance in requirements-driven development.

PURE provides a closer approximation to requirements-first practice because its
requirements were authored independently of the UI evidence selected for this
study. However, PURE was not created as a visual-verification benchmark: most
source requirements have no aligned screenshot sequence, and available figures
often show only a static or partial view. Its curated results are therefore
framed as document-to-UI consistency and reported separately from
implementation-conformance results over recorded execution flows.

### 7.5 Reliability and Reproducibility

Model APIs can return malformed responses, change behavior between versions, or fail transiently. Older flow runs contained API fallbacks, and cached responses may hide differences between repeated executions. The frozen manifests therefore record retries, failures, fallbacks, token counts, image counts, runtime, cache policy, and pricing assumptions.

The repository contains stale summary metrics generated against older benchmark snapshots. For example, one stored batched-top-k metric reports 31.8% accuracy because it evaluates 201 predictions against all 258 current gold items and counts the 57 absent predictions as abstentions. Recomputed metrics restricted to the actual 201-item run give 75.1% accuracy. This discrepancy demonstrates why each thesis table must be generated from a frozen manifest with matching prediction and gold sets.

### 7.6 Current Scope Limitations

The pipeline provides mature step-level evidence and implemented region
grounding, but no benchmark-wide region-quality estimate. Bounding boxes are
not treated as an accuracy intervention. Screenshots cannot
establish hidden backend truth, global absence, long-term persistence, external
delivery, or complete result correctness. The completed 2x2 matrix isolates
claim and screenshot policy for one model, but it does not show that
evidence-first design uniformly improves false fulfillment. The reported
conclusions remain within these limits; evidence grounding alone does not
establish safer labels, and no benchmark-wide region-quality rate is claimed.

\clearpage

### 7.7 Dataset Licensing and Artifact Availability

All 13 primary flows belong to the Mind2Web `test_task` split. Mind2Web is
identified by its maintainers as CC BY 4.0, but the official repository also
asks users not to redistribute unzipped test files online and not to place
benchmark data in training corpora [@mind2webrepo2023]. The public replication artifact is
therefore limited to reviewed derived annotations, sanitized predictions, code,
configurations, citations, and aggregate results. It excludes original
screenshots, HTML, MHTML, HAR files, traces, videos, processed trajectories,
complete test records, and raw model interactions.

The source code and permitted replication materials are available in the public
GitHub repository [@brueck2026artifact]. Frozen run manifests record the exact
repository revisions used for the reported experiments.

PURE 2.0 is marked CC BY 4.0 in its Zenodo metadata [@purezenodo2018]. The
public artifact may therefore include selected and contextualized requirements, reviewed
annotations, and evaluation results with attribution and an indication of
changes. The PURE record also states that its curators did not verify the
license agreements or intellectual-property rights governing every original
Web document and provides a contact for takedown requests. The release retains
that caveat and does not apply the repository's MIT software license to
PURE-derived content. A setup command downloads and verifies the original PURE
archives directly from Zenodo when full reproduction is required.

## 8 Conclusion

### 8.1 Summary

This thesis investigated automated verification of textual UI requirements
against ordered screenshot flows. Its output contract combines a fulfillment
label with identifiable UI evidence and preserves uncertainty when the recorded
flow is insufficient.

To study this task, the thesis introduced an explicit four-label verification
contract, separated UI evaluability from fulfillment, implemented a modular
evidence-first pipeline, and constructed a reviewed 258-item benchmark over 13
Mind2Web-derived flows. The evaluation compared models, claim policies, and
screenshot-selection strategies while reporting label quality, unsafe positive
predictions, abstention, traceability, stability, cost, and qualitative error
patterns. A region-grounding extension adds spatially precise evidence without
being treated as a cause of improved label accuracy.

### 8.2 Answers to the Research Questions

For **RQ1**, multimodal models assess requirement fulfillment from ordered
screenshot flows with useful but incomplete accuracy under the fixed
four-label operationalization. Gemini 3.1 Flash-Lite reaches 79.5% accuracy and
0.511 macro-F1 in the matched raw/all configuration, compared with 73.3% and
0.413 for Gemini 2.5 Flash-Lite. The hosted Qwen baseline shows that equal
headline accuracy can conceal substantially different false-fulfillment and
minority-class behavior. Model choice therefore matters, and accuracy alone
does not characterize fulfillment-label performance.

In the order-unavailable robustness condition, 10.9% of labels change and aggregate accuracy decreases
by about 4.7 percentage points. Ordered input is therefore operationally
relevant to the implemented verifier, although the limited subgroup evidence
does not support a universal causal claim for every temporal requirement
pattern.

For **RQ2**, the effects of decomposition and screenshot selection are
conditional. Gated automatic decomposition does not materially improve
all-screenshot accuracy and increases false fulfillment in that setting, but it
improves macro-F1 when evidence is restricted to top-4. Shared top-4 selection
reduces raw-requirement accuracy and chronological evidence-trace alignment relative to the complete flow
while providing negligible cost savings in the current batching
implementation. Explicit evidence remains valuable for traceability even where
the staged configuration does not improve labels. Region-level evidence is
evaluated as an additional traceability output rather than an accuracy factor.

For **RQ3**, the main failures are systematic. Models over-generalize from a
visible entry point to an unobserved outcome, infer hidden or external behavior
from interface proxies, overstate universal and comparative claims, and miss
decisive late states when retrieval favors lexical overlap.

Native abstentions often protect against unsupported closed-world decisions:
replacing all abstentions with negative labels substantially reduces accuracy.
This does not prove that every abstention is calibrated, but it confirms that
insufficient evidence and visible contradiction must remain distinct.

The completed
screenshot-aware audit assigns 142 of 392 label errors (36.2%) to unsafe
over-fulfillment, 138 (35.2%) to excessive abstention, and 57 (14.5%) to
evidence-selection misses. Multi-screen composition, late result states, hidden
or external behavior, and cross-step persistence are the most frequent
overlapping requirement patterns. The results answer RQ3 descriptively for the
frozen 13-flow benchmark; repeated conditions and the LLM-assisted coding with
targeted primary-author boundary review do not support population-level
prevalence or independent-human reliability claims.

### 8.3 Contributions

The work defines evidence-bounded UI requirement verification over ordered
observations and makes its visible/hidden boundary and label policy explicit. A
modular implementation covers flow ingestion, requirement understanding,
screenshot selection, multimodal claim verification, deterministic
aggregation, evidence localization, annotation, and experiment packaging.

The accompanying benchmark records requirement labels, UI evaluability,
claims, evidence steps, rationales, uncertainty reasons, and contrastive items.
Its reference annotations were produced through prediction-independent
primary-author review. The controlled experiments reveal an
interaction between decomposition and retrieval and show that smaller
screenshot sets can omit decisive evidence without meaningful cost savings.
The evaluation framework keeps screenshot retrieval, region grounding, UI
evaluability, abstention, runtime, cost, and stability as distinct outcomes.

### 8.4 Future Work

The next methodological step is an error-driven refinement loop for the label
policy. After each evaluation, the primary error categories can be inspected
for recurring mechanisms and translated into general evidence-sufficiency
rules. For example, the rubric could distinguish visible states from downstream
effects, bounded UI sets from open-world completeness, and strong visible
proxies from hidden guarantees. The revised guide, prompt, and deterministic
gates would then be evaluated on held-out flows, and the remaining errors would
start the next iteration. This process could reduce model-dependent assumptions
without treating the observed categories as universal causes or assuming that
each iteration must improve accuracy.

This work requires a larger, requirements-first benchmark. Independent
requirements should be fixed before collecting corresponding UI drafts,
implementations, and execution flows, ideally with several variants containing
natural or deliberately introduced deviations. Such data would separate
requirement ambiguity, design conformance, implementation defects, and
incomplete execution evidence. The rubric should be developed separately from
the evaluation applications and tested on held-out contexts. More diverse
interfaces, requirements from real projects, additional flow clusters, and
several reviewers would also strengthen estimates for rare classes and reveal
whether refined rules transfer beyond the current benchmark.

For short flows, future systems should retain direct complete-flow verification
as the baseline because neither mandatory claim decomposition nor shared
lexical top-k selection improved the strongest configuration here. Adaptive evidence
acquisition becomes relevant when flows exceed practical context limits. It
should pair actions with result states, prioritize late states, and request more
screenshots when evidence is insufficient. Finally, region grounding should
improve proposal coverage and support multi-region or transition evidence. Its
success should be measured through relevance, sufficiency, reviewer effort, and
auditability rather than assumed to improve the verification label.

## References Used in This Draft

- Baltes, S. et al. (2026). *Guidelines for Empirical Studies in Software Engineering involving Large Language Models*. Empirical Software Engineering. arXiv:2508.15503.
- Becker, J. et al. (2025). *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*. arXiv:2507.09089.
- Berry, D. M., Kamsties, E., and Krieger, M. M. (2003). *From Contract Drafting to Software Specification: Linguistic Sources of Ambiguity—A Handbook*. University of Waterloo Technical Report.
- Cheng, K. et al. (2024). *SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents*. ACL 2024. DOI: 10.18653/v1/2024.acl-long.505.
- Cleland-Huang, J. et al. (2014). *Software Traceability: Trends and Future Directions*. FOSE 2014. DOI: 10.1145/2593882.2593891.
- Deng, X. et al. (2023). *Mind2Web: Towards a Generalist Agent for the Web*. NeurIPS 2023. arXiv:2306.06070.
- OSU NLP Group (2023). *Mind2Web: Dataset, Code, and Models*. GitHub repository: https://github.com/OSU-NLP-Group/Mind2Web.
- Ferrari, A., Spagnolo, G. O., and Gnesi, S. (2017). *PURE: A Dataset of Public Requirements Documents*. IEEE RE 2017. DOI: 10.1109/RE.2017.29. Current dataset record: 10.5281/zenodo.7118517; original archived version: 10.5281/zenodo.1414117.
- Gervasi, V., Ferrari, A., Zowghi, D., and Spoletini, P. (2019). *Ambiguity in Requirements Engineering: Towards a Unifying Framework*. LNCS 11865, 191–210. DOI: 10.1007/978-3-030-30985-5_12.
- Gou, B. et al. (2025). *Navigating the Digital World as Humans Do: Universal Visual Grounding for GUI Agents*. ICLR 2025.
- Hendrickx, K. et al. (2024). *Machine Learning with a Reject Option: A Survey*. Machine Learning 113, 3073–3110. DOI: 10.1007/s10994-024-06534-x.
- Jimenez, C. E. et al. (2024). *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?* ICLR 2024. arXiv:2310.06770.
- Kretzer, F., Kolthoff, K., Bartelt, C., Ponzetto, S. P., and Maedche, A. (2025). *Closing the Loop between User Stories and GUI Prototypes: An LLM-Based Assistant for Cross-Functional Integration in Software Development*. CHI 2025, Article 879. DOI: 10.1145/3706598.3713932.
- Kwa, T. et al. (2025). *Measuring AI Ability to Complete Long Tasks*. arXiv:2503.14499.
- Massenon, R., Gambo, I., and Khan, J. A. (2026). *Toward an Automated Cross-Multimodal Verification of Mobile App Bug Fixes*. Information and Software Technology 191, 107996. DOI: 10.1016/j.infsof.2025.107996.
- Nass, M., Alégroth, E., and Feldt, R. (2021). *Why Many Challenges with GUI Test Automation (Will) Remain*. Information and Software Technology. DOI: 10.1016/j.infsof.2021.106625.
- Lu, Y., Yang, J., Shen, Y., and Awadallah, A. (2024). *OmniParser for Pure Vision Based GUI Agent*. arXiv:2408.00203.
- Wen, B. et al. (2025). *Know Your Limits: A Survey of Abstention in Large Language Models*. Transactions of the Association for Computational Linguistics 13, 529–556. DOI: 10.1162/tacl_a_00754.
- Yang, J. et al. (2023). *Set-of-Mark Prompting Unleashes Extraordinary Visual Grounding in GPT-4V*. arXiv:2310.11441.
- Zheng, B. et al. (2024). *GPT-4V(ision) is a Generalist Web Agent, if Grounded*. ICML 2024, PMLR 235.
- Brück, B. (2026). *UI Requirement Verification: Source Code and Replication Materials*. GitHub repository: https://github.com/benno-tum/ui-requirement-verification.
