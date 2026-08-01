# Thesis intent and readability review — 1 August 2026

## Scope and method

This review covers the complete LaTeX thesis, the requirement-generation and
verification code paths, the frozen Mind2Web annotations, existing thesis audit
notes, and the relevant Codex task history. The main question was not only
whether the thesis states *what* was done, but whether it explains *why that
choice was reasonable, what alternatives were available, and what the choice
does not establish*.

The review led to direct edits in Chapters 1, 2, 4, 5, 6, and 7 and to a new
benchmark-construction figure. The remaining issues below are ordered by
importance.

## First review pass: completed items

### 1. Explain how the 13 flows were selected

**Passage:** Chapter 5, “Main Flow Dataset,” beginning “The selected flows
cover…”

The repository makes the 13-flow set reproducible through
`data/annotations/flow_manifests/mind2web_repo_dataset_annotation_ids.txt`, but
neither the thesis, the manifest, nor the commit that introduced it states why
these 13 flows were chosen. Older notes mention 13 flows selected from 39 locally
processed flows, while the export process scans a still larger Mind2Web split.

This argument is now integrated. Chapter 5 states that the 13 flows were a
purposive convenience sample from 39 locally processed flows, selected for
complete ordered screenshots and coverage of search, navigation, forms, carts,
checkout, and result states. It also states that this is not a random or
representative Mind2Web sample.

### 2. Make source and contrastive requirements easy to understand

**Passage:** Chapter 5, “Main Flow Dataset” and “From Candidates to
Verification Gold.”

The final benchmark now has a simple description:

- 187 source requirements are ordinary requirements derived from the flows;
- 71 contrastive requirements are reviewed variants that deliberately add or
  strengthen an obligation;
- all 258 are completed verification-gold items.

The 21 reviewed ordinary records that still lived in candidate storage were
checked for ID conflicts and meaningful duplicates and then promoted to gold.
No unfinished ordinary candidate is now counted as a benchmark item. The
thesis no longer explains internal storage fields because they are not needed
to understand the method.

### 3. Add the source-versus-contrastive result

**Passages:** Chapter 5 says the two groups are reported separately where
construction matters; Chapter 7 repeats that claim under internal validity.

Chapter 6 now contains the primary raw/all result split by construction. Source
requirements reach 88.8% accuracy and 5.3% false fulfillment; contrastive
requirements reach 56.3% accuracy and 52.6% false fulfillment. The text also
warns that the two groups have deliberately different label distributions, so
this is a descriptive breakdown rather than a causal difficulty comparison.

### 4. Resolve and retain the screenshot-order shuffle test

**Passage:** Chapter 6, “Order-Unavailable Robustness Result,” beginning
“Against the current working gold snapshot…”

The mismatch came from one AMC gold-label correction made between the two run
manifests: `REQ-05` changed from `PARTIALLY_FULFILLED` to `FULFILLED`. Its text
did not change, and the verifier input loader does not expose gold labels. Both
frozen outputs were rescored against the corrected reference. The result is
79.8% ordered versus 75.2% shuffled. Chapter 6 now calls this the
“Screenshot-Order Shuffle Test” and explains both the correction and the scope
of the intervention in plain language.

### 5. Report the completed auxiliary reviews

**Passages:** Chapter 6, “UI-Evaluability Analysis” and “Region-Grounding
Pilot.”

Both reviews were complete; the older thesis wording was wrong.

- The 81-item UI-evaluability review contains 81 resolved decisions. It retains
  51 labels, adopts the rule-based label in 27 cases, and chooses another label
  in three. The 30 changed labels now override the earlier values in the
  benchmark and PURE records.
- The region form contains 60 completed reviews: 52 returned-region items and
  eight no-region items. The thesis now reports geometric validity, relevance,
  sufficiency, and no-region correctness for this targeted author audit.

The two reviews answer different questions. Only the UI-evaluability review
changes benchmark UI-evaluability labels. The region review evaluates the
quality of predicted boxes and does not change fulfillment or UI-evaluability
labels.

## Intent and alternatives audit

### Why use a multimodal language model?

**Status: fixed in Chapter 4, “Multimodal Claim Verification.”**

The revised passage now states the actual task fit: the verifier must connect
open-ended requirement language with visible text, controls, icons, layout,
state, and multi-screen transitions. OCR plus a text classifier loses non-text
and spatial evidence; a fixed-label image classifier does not naturally accept
new textual requirements at inference time. A pretrained multimodal language
model supplies both modalities and open-vocabulary reasoning in one component.

The passage also explains why this thesis does not fine-tune a task-specific
model. There are only 258 labels from 13 correlated flows. Training on them
would consume the already small independent evaluation set and would not supply
the interface, requirement, and transition diversity needed to learn the task
from scratch. Collecting a separate training corpus is outside the thesis scope.

Terminology note: fine-tuning is not synonymous with reinforcement learning.
The relevant alternatives are supervised fine-tuning, preference/RL-based
adaptation, training a task-specific vision-language classifier, OCR plus
text/rules, and executable GUI testing. The thesis should use “training or
fine-tuning a task-specific model” unless a specific RL method is actually meant.

The rationale is intentionally modest: it explains why a pretrained MLLM is a
pragmatic choice, not why MLLMs are inherently optimal. The deterministic and
hosted open-weight baselines then test narrower alternatives without training on
the benchmark.

### Why generate requirements from the flows?

**Status: fixed in Chapter 5.**

There is no independent requirements specification for the selected Mind2Web
trajectories. Generation therefore bootstraps plausible requirement--evidence
pairs. The revised text now states the cost of this choice: it reverses normal
requirements-first development, favors behavior already visible in the UI, and
does not measure naturally occurring implementation defects.

The harvesting prompt in
`src/ui_verifier/requirements/prompting.py` confirms the intended breadth. It
asks for full-flow reasoning, feature- or workflow-level statements, wording
that survives widget or label changes, indirect flow-grounded items, and nearby
variants. It explicitly treats the UI as evidence rather than as a widget
inventory and allows requirements that are not fully satisfied or fully
UI-verifiable.

### How strongly were generated requirements automatically filtered?

**Status: clarified in Chapter 5; retain this limitation.**

The candidate prompt offers `DIRECT_INCLUDE`, `REWRITE_TO_VISIBLE_CORE`, and
`EXCLUDE_FROM_VERIFICATION_BENCHMARK`; the normalizer can also reject
non-verifiable items and duplicates. However, the stored artifacts show that
this was not a strong automatic funnel:

- the 268 generated candidate records contain 267 direct includes and one
  exclusion;
- the 100 versioned candidate records contain 99 direct includes and one
  exclusion;
- the generated directories combine snapshots and imported contrastives, so
  268 must not be reported as a clean stage count.

The thesis now says that automatic decisions were proposals and that author
review performed the decisive filtering, editing, promotion, and evidence
annotation. Avoid wording such as “the model filtered the broad harvest into a
high-quality benchmark”; the stored decisions do not support that strength of
claim.

### Why were contrastive requirements needed?

**Status: fixed in Chapter 5.**

The broad prompt did ask for hidden, partial, and unsupported properties, but
the source set remained strongly positive: among 187 semantically ordinary
requirements, 164 are fulfilled, 13 partial, nine abstaining, and one negative.
This is expected when requirements are inferred from interfaces that already
show the described behavior.

The contrastive stage deliberately changes reviewed source requirements using
completeness, persistence, external-effect, missing-step, comparison,
consistency, and stronger-constraint mutations. This provides difficult
non-positive cases, but it changes the benchmark distribution and does not
estimate natural defect prevalence. The intended label is a generation target,
not truth. The data provides strong evidence for that distinction: the final
reviewed label differs from the target for 42 of 71 contrastive items.

### Does the verifier know whether an item is normal or contrastive?

**Status: now disclosed in Chapter 7, but a rerun would be stronger.**

The input loader excludes `source_type`, intended labels, reference labels,
evidence, and rationales. It passes requirement text, frozen claim text where
applicable, metadata, and `requirement_id`. The batched model payload includes
that identifier. Because all 71 contrastive items use a `CONTR-` prefix, the
model can infer semantic provenance even though it cannot see the intended
target label.

The existing experiment is therefore target-label-blind but not
provenance-blind. The strict fix is to replace prompt-facing IDs with opaque
per-flow IDs and rerun the primary cells. If that is infeasible, retain the
limitation and do not say that normal and contrastive provenance was hidden.

### Other design choices whose intent is already sufficiently explained

- Ordered flows rather than isolated screenshots: Chapter 2 connects them to
  transitions and later result states, and the order-unavailable robustness
  condition tests their relevance.
- Lexical top-4 retrieval: Chapter 4 explains that it is deterministic,
  inexpensive, and reproducible, and explicitly treats it as a baseline rather
  than a semantic optimum.
- Conservative four-label aggregation: Chapters 3 and 4 explain why missing
  evidence is distinct from visible contradiction and why `ABSTAIN` is not a
  system failure.
- Step evidence versus bounding boxes: Chapters 3--6 keep trace quality,
  localization, and classification as different constructs.
- A generic evidence-sufficiency policy: Chapter 7 explains that a more detailed
  policy derived from only 13 flows would risk fitting the rubric to the test
  applications.
- Direct prompting versus the staged pipeline: Chapters 1 and 7 correctly state
  that the stages mainly improve diagnosis and traceability; they do not claim a
  uniform accuracy gain.

## Readability and AI-style audit

The main problem is not isolated vocabulary. It is repeated definitions,
development chronology in the result narrative, and paragraphs that carry too
many qualifications at once. The following cuts would improve the thesis most.

| Priority | Passage | Problem | Recommended edit |
|---|---|---|---|
| High | Chapter 6, sections before “Controlled Full-Benchmark Comparison” | The reader encounters metrics, two auxiliary protocols, an error taxonomy, qualitative patterns, and an example before seeing the primary result. | Move the primary comparison directly after the shared metric definitions. Place error patterns after the quantitative results. Move auxiliary protocols/results after the main RQs. |
| High | Chapter 6, “Dominant Error Patterns” opening | “Historical… current… final…” narrates drafting history and still provides no final category counts. | Say simply that earlier review informed the taxonomy and mark every following statement as qualitative unless a denominator is supplied. |
| Addressed | Chapter 6, shuffle-test paragraph | The ordered anchor and main table used different reference revisions. | Both frozen outputs are now rescored against the corrected reference, and the one-label change is explained. |
| Addressed | Chapter 2, opening literature-search protocol | The exact Boolean query and ranked-screening narrative occupied almost a page before the conceptual chapter began. | Shortened to the search date, concept blocks, screening depth, exclusions, and closest papers. The exact record remains in the existing search log. |
| Medium | Chapter 3 label semantics and Chapter 5 annotation schema | The original draft defined the same labels twice. | Already shortened Chapter 5 to point to the canonical definitions in Chapter 3. |
| Medium | Chapter 6 metric definitions versus Chapter 3 operationalization | Several concepts are explained twice. | Keep the construct rationale in Chapter 3; in Chapter 6 use formulas/operational details and avoid re-explaining the motivation. |
| Medium | Chapter 7, “Construct Validity” | Six different construct issues appear as equally weighted dense paragraphs. | Group them into three short themes: verdict threshold; evidence localization; evaluability and claim matching. |
| Medium | Chapter 5 “Data Governance” and Chapter 7 licensing | The same release exclusions appear twice. | Keep a two-sentence dataset boundary in Chapter 5 and the full rationale in Chapter 7, or move the procedural list to the artifact README. |
| Medium | Chapter 8, RQ1 answer | Model comparison, class imbalance, order result, and causal caveat are compressed into one paragraph. | Split after the model comparison; give the order result its own short paragraph. |
| Low | Chapter 1 related-work/approach paragraphs | Long enumerations of pipeline components sound catalog-like. | Prefer one claim per sentence and let the architecture figure carry component detail. |

### Concrete shorter replacements

**Chapter 2 opening:**

> Related work was identified through a targeted Google Scholar search on 30
> July 2026. The search combined requirements or user-story terms with GUI or
> screenshot terms, verification or traceability terms, and LLM or multimodal
> model terms. The first 20 ranked results were screened for studies that linked
> textual software artifacts to GUI evidence through a verification-like
> decision. The exact query and screening log are provided in the replication
> material. The closest studies are Kretzer et al., Massenon et al., and
> GUISpector.

**Chapter 6 error-pattern opening:**

> Earlier reviews were used to define the error taxonomy. The following patterns
> summarize the controlled runs qualitatively; numerical frequencies are given
> only where a frozen denominator is available.

**Chapter 7 construct-validity opening:**

> The four labels encode a conservative policy for screenshot evidence. Another
> project might treat missing evidence as failure or accept a visible success
> message as proof of a backend outcome. The labels are therefore an explicit
> safety-oriented operationalization, not the only valid definition of
> fulfillment.

## Edits already made

- Simplified the Introduction problem statement and changed RQ3 from causal
  “patterns that cause” wording to “patterns associated with.”
- Added the MLLM-versus-training rationale and model-selection rationale to
  Chapter 4.
- Rewrote the requirement-generation section around actual intent, limitations,
  human review, and contrastive enrichment.
- Corrected the source/contrastive counts to 187/71, promoted the remaining 21
  reviewed ordinary items, and removed internal storage terminology from the
  thesis explanation.
- Added the empirical fact that 42 of 71 contrastive target labels changed after
  review.
- Added the prompt-facing `CONTR-` provenance-cue limitation.
- Removed the superseded 201-item preliminary label/evidence result block from
  Chapter 6.
- Applied the completed 81-item UI-evaluability reinspection and reported the
  completed 60-item region audit with explicit scope limits.
- Added the source-versus-contrastive result table and resolved the shuffle-test
  reference mismatch.
- Removed a distracting repository-history example from the reproducibility
  discussion and simplified several dense paragraphs.
- Shortened the duplicated annotation-label definitions in Chapter 5.
- Reduced the Chapter 2 search protocol from a page-like query narrative to one
  methodological paragraph.

## Diagram recommendation and implementation

The best additional visual belongs in Chapter 5 immediately after the
source-versus-contrastive construction explanation. This is the point where the
reader otherwise has to remember harvesting, candidate refinement, author
review, contrastive mutation, intended labels, and final evidence review.

`thesis/figures/benchmark_construction_funnel.tex` now shows that process and
the 187 + 71 = 258 semantic split. It complements the existing Chapter 4
architecture figure instead of duplicating it: the architecture figure explains
inference, while the new figure explains how the evaluation data was created.

## Recommended final editing order

1. Reorder Chapter 6 so primary results precede qualitative findings.
2. Perform the smaller Chapter 7 and Conclusion paragraph cuts.
3. Decide whether to rerun the primary verifier with opaque prompt-facing IDs or
   retain the concise identifier-cue limitation.
4. Complete a final sentence-level pass for dense and repetitive prose.
