from __future__ import annotations

import json


def build_prompt(task: dict, selected_steps: list[int]) -> str:
    confirmed_task = task.get("confirmed_task", "")
    website = task.get("website", "")
    domain = task.get("domain", "")

    return f"""
You are given an ordered screenshot sequence of a web UI flow.

Task description:
{confirmed_task}

Website:
{website}

Domain:
{domain}

The visible screenshots correspond to these REAL flow step indices:
{selected_steps}

Important:
- The values in evidence_steps MUST use the real flow step indices listed above.
- Do NOT renumber the screenshots as 1, 2, 3, ...
- If the visible screenshots are from steps [1, 5, 10, 14], then valid evidence_steps are [1], [5, 10], or [14].

Your job:
Generate harvested requirement hypotheses from the visible UI flow.

These are NOT final benchmark items.
They are broad requirement hypotheses that will later be normalized into candidate and gold requirements.

Core objective:
Produce a comprehensive harvested requirement set that captures what the system or service appears to do, how the visible workflow is supported, and which nearby requirements are strongly suggested by the flow.

Work process you should follow internally before answering:
1. Understand the overall system or service represented by the full sequence.
2. Identify the major workflow phases across the ordered screenshots.
3. Identify the most important user-facing capabilities visible in those phases.
4. Generate harvested requirements that cover the meaningful capability space suggested by the flow.
5. Only then finalize the JSON output.

Coverage guidance:
- Use the full ordered sequence, not just the first or most visually obvious screen.
- Try to cover the main functional phases of the flow when they support distinct meaningful requirements.
- Do NOT stop after only a few obvious requirements if the flow supports more.
- Do NOT impose an artificial upper bound on the number of requirements.
- Return all meaningful harvested requirements that remain close to the shown system.
- Think of the harvested requirements as the foundation that lead to this UI flow

Conceptual distinction:
- flow_overview and capability_summary describe the application or service at a high level.
- harvested requirements describe concrete software capabilities, workflow support, visible behavior, or disciplined nearby variants.
- A very abstract service description is useful as metadata, but should not automatically become a requirement unless it is also a meaningful concrete software requirement.

Harvesting stance:
- Focus on meaningful software features, capabilities, workflow support, and visible user-facing behavior.
- The UI is grounding evidence for the requirement, not the main subject of the requirement.
- Prefer requirements that would still make sense if the exact layout, widget choice, or field label changed.
- It is acceptable that not all harvested requirements are fully satisfied by the current screenshots.
- Stay close to the shown system, task, website, and domain.
- Do NOT invent completely unrelated product capabilities.

Grounding scopes:
1. DIRECT_FLOW_GROUNDED
   - clearly supported by the visible screenshots and their ordering

2. INDIRECT_FLOW_GROUNDED
   - not fully shown end to end, but implied by visible UI cues, task context, or surrounding flow structure
   - use this when the flow gives a basis for inference without fully demonstrating the whole requirement
   - be creative here

3. NEARBY_VARIANT
   - a disciplined close variant that a similar system in the same domain would plausibly support
   - use this sparingly and when it remains anchored to the visible feature space
   - be creative here

Guidance for INDIRECT_FLOW_GROUNDED:
- Good indirect items extend what is already visible.
- They should feel like a natural inference from the actual flow, not from general world knowledge alone.

Guidance for NEARBY_VARIANT:
- Good nearby variants stay close to the visible feature space.
- They often extend an already visible capability by one plausible step, refinement, or user need.
- They should still feel natural for this specific system type.
- Omit weak speculative variants.

Common web-flow requirement families that may help orient your thinking:
- search, filtering, sorting, and result discovery
- list-to-detail navigation
- navigation between major sections or steps
- selection and configuration of options
- booking, checkout, review, or application flows
- authentication, sign-in, registration, or gated access
- visible feedback, validation, or confirmation
- cross-screen consistency and state carry-over
- transparent comparison of options, plans, or prices
- settings, preferences, language, or date selection

Important:
- These families are examples, not mandatory categories.
- Do NOT force requirements into these families if the shown flow suggests something else.
- The best requirement may be broader than any one visible widget.

Requirement quality guidance:
- Prefer broader, feature-level statements when the screenshots support them.
- Requirement sets should not be dominated by tiny field-level widget claims.
- Treat screenshots as grounding evidence for broader product or workflow requirements, not merely as an inventory of visible controls.
- Many realistic requirements are not fully UI-verifiable from screenshots alone.
- Many others have a visible UI-observable core but also hidden-state, policy, data, or external-system aspects.
- Requirement quality and coverage are more important than perfectly precise labels.
- Use the labels as best-effort harvest metadata, not as a formal proof.

Role and perspective guidance:
- A role is optional.
- Introduce a role only when it improves specificity and is plausibly supported by the task or UI context.
- Roles like user, customer, applicant, authenticated user, or account owner may be used when naturally suggested.
- Avoid inventing high-privilege roles such as admin, moderator, or back-office staff unless the UI clearly suggests a management or privileged interface.

Before emitting a narrow widget requirement, ask:
- Can this be merged into a broader requirement about the workflow phase?
- Is this a visible manifestation of a broader requirement?
- Is this genuinely useful as a later benchmark item?
- Would this still be a sensible requirement if the exact field label or example value changed?

Low-value items to avoid unless they are clearly task-critical:
- "The system shall display a first name field."
- "The system shall display a last name field."
- "The system shall display an email field."
- generic button, label, or field presence with no broader verification value
- conceptual UI implementation statements that only describe a specific widget layout
- harvested items that simply restate one entered value from the task instance

Examples of stronger requirement formulations with possible visible triggers:
- "The system shall collect pickup details including location, date, and time."
  Why strong: groups related visible inputs into one feature-level requirement.
  Possible UI artifacts: grouped booking form, location input, date picker, time selector.

- "The system shall carry previously selected rental details forward into later checkout steps."
  Why strong: captures cross-screen consistency instead of isolated fields.
  Possible UI artifacts: booking summary card, prefilled values, review step, persistent itinerary summary.

- "The system shall allow the user to configure optional add-ons and reflect those choices in the UI."
  Why strong: describes a configurable feature and its visible manifestation.
  Possible UI artifacts: option cards, toggles, selected extras, updated summary or price display.

- "The system shall provide visible progress guidance across the booking flow."
  Why strong: captures workflow support and visible guidance.
  Possible UI artifacts: stepper, breadcrumb, progress indicator, section titles such as review or payment.

- "The system shall support discoverability of items through search and filtering."
  Why strong: broader than one search field and reusable across websites.
  Possible UI artifacts: search box, filter controls, active filter chips, result list, no-results state.

- "The system shall provide transparent comparison information for plan or ticket options."
  Why strong: reflects a visible decision-support capability.
  Possible UI artifacts: plan cards, feature comparisons, price breakdowns, side-by-side options.

- "The system shall maintain consistency between selected filter criteria and displayed results."
  Why strong: captures state consistency rather than one control.
  Possible UI artifacts: active filters, selected facets, filtered result counts, persistent sort or filter indicators.

Examples of acceptable visible NFR-like hypotheses when grounded in the UI:
- "The system shall provide clear progress guidance during checkout."
- "The system shall present pricing and option details transparently enough for comparison."
- "The system shall provide visible feedback when a filter or configuration choice becomes active."
- "The system shall keep user-selected context consistent across subsequent screens."

Rules:
- Generate software requirements, not user goals, not test instructions, not business objectives.
- Use declarative requirement style such as "The system shall ..."
- Prefer singular but meaningful items. Merge closely related local observations when appropriate.
- Use screenshots plus task context, but do not invent hidden backend behavior as visible fact.
- A requirement does not need to be fully satisfied by the current screenshots to be worth harvesting.
- If evidence is weak, give it lower confidence
- Prefer a complete harvested set over a short conservative one, as long as the items remain meaningful and close to the shown system.

Classification guidance:
- UI_VERIFIABLE:
  largely judgeable from ordered screenshots alone
- PARTIALLY_UI_VERIFIABLE:
  a visible core exists, but full satisfaction also depends on hidden state, external delivery, policy, timing, or broader context
- NOT_UI_VERIFIABLE:
  mainly backend, timing, security, architecture, hidden data correctness, or too abstract for screenshot-based judgment

Allowed values:
- grounding_scope: DIRECT_FLOW_GROUNDED | INDIRECT_FLOW_GROUNDED | NEARBY_VARIANT
- requirement_type: FR | NFR | UNCLEAR
- ui_evaluability: UI_VERIFIABLE | PARTIALLY_UI_VERIFIABLE | NOT_UI_VERIFIABLE
- task_relevance: HIGH | MEDIUM | LOW
- confidence: HIGH | MEDIUM | LOW

Output requirements:
- Do not force all items to be UI_VERIFIABLE.
- Do not force all items to be FR.
- Do not force nearby variants if the flow does not support them.
- Prefer broader workflow or feature-level requirements over many tiny local ones.
- Include partially UI-verifiable or visible NFR-like items when they arise naturally from the flow.
- Include indirect and nearby items only when they are disciplined and useful.
- visible_core_candidate is optional and should only be filled when there is an obvious concise visible core.

Return ONLY valid JSON in this format:
{{
  "flow_overview": "One concise description of what kind of system or service this flow appears to represent.",
  "capability_summary": [
    "Short capability phrase 1",
    "Short capability phrase 2"
  ],
  "requirements": [
    {{
      "id": "HARV-01",
      "harvested_text": "The system shall ...",
      "grounding_scope": "DIRECT_FLOW_GROUNDED",
      "requirement_type": "FR",
      "ui_evaluability": "PARTIALLY_UI_VERIFIABLE",
      "task_relevance": "HIGH",
      "evidence_steps": [5, 10],
      "confidence": "MEDIUM",
      "rationale": "Why this hypothesis is grounded in the visible flow and why the classification is plausible.",
      "visible_core_candidate": null
    }}
  ]
}}

Return a comprehensive, non-trivial harvested set grounded in the screenshots and task context.
""".strip()


def build_candidate_rewrite_prompt(harvest_payload: dict) -> str:
    harvest_json = json.dumps(harvest_payload, indent=2, ensure_ascii=False)

    return f"""
You are given harvested requirement hypotheses extracted from an ordered UI screenshot flow.

Your task is to rewrite them into candidate requirements for a reviewable requirement dataset that will later support UI verification.

Goal:
Produce reviewable candidate requirements that preserve the useful breadth of the harvested set while removing redundancy, over-speculation, and low-value items.

Important principles:
- Candidate requirements are usually narrower and more reviewable than harvested requirements.
- However, do NOT create trivial field-by-field items unless they are independently meaningful.
- Merge low-value local observations into one broader candidate when they belong to the same visible UI function.
- Preserve the original semantic intent of the harvested item.
- Keep the requirement focused on a feature or capability, not on a conceptual widget layout.
- Prefer visible, reviewable verification units.
- Candidate requirements are NOT restricted to fully UI-verifiable items.
- If the harvested item is only partially UI-verifiable, either keep the broader requirement as a candidate or rewrite it to its visible core, depending on which version is the more meaningful reviewable verification unit.
- Nearby variants may remain as candidates if they are close enough to the shown system and useful for the later dataset.
- Drop weak, redundant, overly speculative, or purely task-instance-specific items.

What makes a good candidate requirement:
- It is meaningful as a verification unit.
- It can be reviewed by a human annotator.
- It is not just a restatement of a single filled value from one screenshot.
- It has a clear visible manifestation in one screen or across a short ordered sequence, or it is still worth keeping because its broader formulation is useful for later partial or abstaining verification.
- It avoids hidden backend claims unless the broader candidate remains meaningful or the visible core is explicitly extracted.
- It helps represent the application or service in a conceptually meaningful way when read together with the other candidates.

Rewrite policy:
1. Keep strong broader items when they remain reviewable.
2. Preserve feature-level wording when it remains visibly reviewable; do not automatically collapse to widget-level phrasing.
3. For partially UI-verifiable harvested items, choose between:
   - keeping the broader requirement as the candidate, or
   - rewriting to a visible-core candidate,
   whichever is the more useful reviewable dataset item.
4. Keep disciplined nearby variants when they remain close to the shown system and add useful coverage.
5. Merge repetitive local field items into one candidate.
6. Remove duplicates and near-duplicates.
7. Remove claims that depend too strongly on example-specific data values.
8. Prefer requirements about:
   - workflow support
   - navigation outcomes
   - state carry-over
   - visible feedback
   - visible selection and configuration options
   - grouped information collection
   - consistency between user choices and later screens
   - meaningful nearby variants suggested by the same service concept
9. Avoid trivial candidates such as:
   - The system shall display a first name field.
   - The system shall display a last name field.
   - The system shall display an email field.
   - The system shall display a button, label, or dropdown when the real requirement is a broader feature.
   unless no better grouped candidate exists.

Decision labels:
- DIRECT_INCLUDE:
  keep the harvested requirement as a candidate with at most light cleanup
- REWRITE_TO_VISIBLE_CORE:
  the broader harvested item is less reviewable, and a visible-core rewrite makes a better candidate
- EXCLUDE_FROM_VERIFICATION_BENCHMARK:
  weak, redundant, overly speculative, or not useful as a benchmark item

Origin labels:
- DIRECT_FROM_HARVEST
- VISIBLE_CORE_REWRITE

Classification guidance:
- UI_VERIFIABLE:
  largely judgeable from ordered screenshots alone
- PARTIALLY_UI_VERIFIABLE:
  a visible core exists, but full satisfaction also depends on hidden state, external delivery, policy, timing, or broader context
- NOT_UI_VERIFIABLE:
  mainly backend, timing, security, hidden data correctness, or too abstract for screenshot-based judgment

Allowed values:
- grounding_scope: DIRECT_FLOW_GROUNDED | INDIRECT_FLOW_GROUNDED | NEARBY_VARIANT
- requirement_type: FR | NFR | UNCLEAR
- ui_evaluability: UI_VERIFIABLE | PARTIALLY_UI_VERIFIABLE | NOT_UI_VERIFIABLE
- non_evaluable_reason: NONE | BACKEND_HIDDEN_STATE | PERFORMANCE_TIMING | SECURITY_PRIVACY | EXTERNAL_INTEGRATION | TOO_ABSTRACT | BUSINESS_RULE_NOT_VISIBLE | DATA_CORRECTNESS_NOT_VISIBLE
- visible_subtype: NONE | TEXT_OR_ELEMENT_PRESENCE | NAVIGATION_OUTCOME | STATE_CHANGE_ACROSS_SCREENS | VALIDATION_OR_FEEDBACK | CONTENT_UPDATE | LAYOUT_POSITION

Output requirements:
- Preserve or refine flow_overview and capability_summary when helpful.
- Keep source_harvest_id.
- Assign a candidate id like REQ-01.
- Keep or refine grounding_scope, requirement_type, and ui_evaluability.
- Add visible_subtype and non_evaluable_reason at this stage.
- Use benchmark_decision = DIRECT_INCLUDE, REWRITE_TO_VISIBLE_CORE, or EXCLUDE_FROM_VERIFICATION_BENCHMARK.
- Use candidate_origin = DIRECT_FROM_HARVEST or VISIBLE_CORE_REWRITE.
- Add normalization_notes explaining the rewrite decision.
- Do not impose an artificial upper bound on the number of candidates.
- Return all strong, de-duplicated, benchmark-useful candidates.

Return ONLY valid JSON in this format:
{{
  "flow_overview": "Optional refined one-line description of the system or service represented by the flow.",
  "capability_summary": [
    "Short capability phrase 1",
    "Short capability phrase 2"
  ],
  "requirements": [
    {{
      "id": "REQ-01",
      "source_harvest_id": "HARV-01",
      "candidate_text": "The system shall collect purchaser contact information including name, email address, and postal code.",
      "grounding_scope": "DIRECT_FLOW_GROUNDED",
      "requirement_type": "FR",
      "ui_evaluability": "UI_VERIFIABLE",
      "non_evaluable_reason": "NONE",
      "visible_subtype": "TEXT_OR_ELEMENT_PRESENCE",
      "benchmark_decision": "DIRECT_INCLUDE",
      "candidate_origin": "DIRECT_FROM_HARVEST",
      "normalization_notes": "Merged multiple local form-field observations into one reviewable candidate."
    }}
  ]
}}

Here are the harvested requirements:
{harvest_json}

Return all strong, de-duplicated, reviewable candidate requirements.
""".strip()


def build_contrastive_from_gold_prompt(
    task: dict,
    gold_payload: dict,
    *,
    target_partially: int,
    target_abstain: int,
    target_not_fulfilled: int,
) -> str:
    confirmed_task = task.get("confirmed_task", "")
    website = task.get("website", "")
    domain = task.get("domain", "")
    gold_json = json.dumps(gold_payload, indent=2, ensure_ascii=False)

    return f"""
You are given accepted gold requirements for a single ordered web UI flow.

Task description:
{confirmed_task}

Website:
{website}

Domain:
{domain}

Your job:
Generate additional contrastive candidate requirements for the same product and task space.

These are NOT gold requirements.
They are reviewable candidate requirements that will later be verified against the UI flow and then reviewed by a human.

Core objective:
Produce realistic new candidate requirements that stay close to the same software capability space as the accepted gold set, but increase coverage of requirements that are likely to end up as:
- partially_fulfilled
- abstain
- not_fulfilled

Important:
- The target label is only a generation target, not truth.
- You are not assigning final benchmark labels.
- You are generating candidate requirements that are plausible for this system and useful for later verification and review.

What you are given:
- a task description
- website and domain context
- optional flow overview and capability summary
- accepted gold requirements for this flow

What you are NOT given:
- screenshots
- hidden system behavior
- backend state
- proof that a generated requirement is satisfied or violated

Generation stance:
- Stay in the same product, workflow, and feature space as the source gold requirements.
- Use the gold requirements as your main anchor, not the exact UI wording.
- Generate requirements that would still make sense if the exact layout or widget choices changed.
- Prefer meaningful software capabilities, workflow support, consistency expectations, visible outcomes, and realistic nearby variants.
- Avoid random speculation and avoid unrelated capabilities.
- Avoid direct paraphrases of the source gold requirements.
- Avoid tiny field-level requirements unless they are independently meaningful.
- Avoid requirements that merely restate task-instance values such as one exact email address, one amount, one city, or one personal name.

Main design goal:
The new requirements should diversify the later verification label distribution while remaining realistic and useful.
A good generated item should still feel like a requirement a human could plausibly have written for the same system.

Controlled mutation families:
Use only these mutation families.

1. persistence_extension
   - extends a visible flow requirement with persistence across later screens, later sessions, or remembered context

2. external_effect_extension
   - extends a visible action toward an external or downstream effect such as delivery, notification, export, or confirmation outside the visible flow

3. policy_or_role_extension
   - adds account, permission, ownership, authentication, or policy constraints that are plausible for the same feature space

4. hidden_state_extension
   - adds a realistic hidden-state or backend-dependent condition while keeping a visible user-facing core

5. completeness_or_universal_quantifier
   - strengthens a requirement toward completeness, coverage, all relevant items, or never/always style expectations
   - use carefully and realistically

6. missing_visible_step
   - adds a plausible visible workflow phase that is not necessarily shown, such as review, edit, confirmation, comparison, progress guidance, or summary

7. stronger_visible_constraint
   - strengthens a visible expectation in a way that remains UI-observable, for example comparison support, clearer transparency, stronger carry-over, richer filtering, or additional visible feedback

8. cross_screen_consistency_extension
   - strengthens consistency across steps, such as carry-over, editable review, retained selections, synchronized summaries, or matching criteria and results

9. nearby_capability_variant
   - a disciplined close variant in the same service concept, used only when it remains tightly anchored to the existing gold set

How mutation families relate to intended labels:
- likely partially_fulfilled:
  persistence_extension
  external_effect_extension
  policy_or_role_extension
  hidden_state_extension

- likely abstain:
  hidden_state_extension
  completeness_or_universal_quantifier
  policy_or_role_extension

- likely not_fulfilled:
  missing_visible_step
  stronger_visible_constraint
  cross_screen_consistency_extension
  nearby_capability_variant

Requirement quality guidance:
- Generate software requirements, not user goals, not test instructions, not business goals.
- Use declarative style such as "The system shall ..."
- Prefer feature-level or workflow-level statements over widget inventories.
- Preserve realism and closeness to the same system.
- Good items often describe workflow support, visible outcomes, consistency, feedback, transparency, or a realistic extension of an existing capability.
- It is acceptable that some generated requirements are broader than what screenshots alone can fully settle.
- Requirement quality matters more than hitting quotas with weak items.

Negative guidance:
Do NOT generate:
- random capabilities from the wider domain that are not suggested by the source gold set
- admin or back-office requirements unless clearly implied
- implementation details or UI layout prescriptions with no broader verification value
- trivial variants that differ only by one noun
- exact copies or near-copies of the source gold text
- requirements that are obviously absurd for the website or task

Diversity guidance:
- Spread the generated items across multiple source gold requirements when possible.
- Use different mutation families.
- Do not create a whole set of near-duplicates.
- Return fewer items rather than weak filler.

Classification guidance:
Use these fields as best-effort metadata for later review.

Allowed values:
- intended_label: partially_fulfilled | abstain | not_fulfilled
- mutation_family:
  persistence_extension
  external_effect_extension
  policy_or_role_extension
  hidden_state_extension
  completeness_or_universal_quantifier
  missing_visible_step
  stronger_visible_constraint
  cross_screen_consistency_extension
  nearby_capability_variant
- grounding_scope: DIRECT_FLOW_GROUNDED | INDIRECT_FLOW_GROUNDED | NEARBY_VARIANT
- requirement_type: FR | NFR | UNCLEAR
- ui_evaluability: UI_VERIFIABLE | PARTIALLY_UI_VERIFIABLE | NOT_UI_VERIFIABLE
- non_evaluable_reason: NONE | BACKEND_HIDDEN_STATE | PERFORMANCE_TIMING | SECURITY_PRIVACY | EXTERNAL_INTEGRATION | TOO_ABSTRACT | BUSINESS_RULE_NOT_VISIBLE | DATA_CORRECTNESS_NOT_VISIBLE
- visible_subtype: NONE | TEXT_OR_ELEMENT_PRESENCE | NAVIGATION_OUTCOME | STATE_CHANGE_ACROSS_SCREENS | VALIDATION_OR_FEEDBACK | CONTENT_UPDATE | LAYOUT_POSITION
- confidence: HIGH | MEDIUM | LOW

Quota guidance:
Try to generate:
- {target_partially} items targeting partially_fulfilled
- {target_abstain} items targeting abstain
- {target_not_fulfilled} items targeting not_fulfilled

But do NOT pad with weak items just to hit the target.
Return only strong, distinct, realistic candidates.

Source material:
{gold_json}

Return ONLY valid JSON in this format:
{{
  "flow_overview": "Optional refined one-line description of the system or service represented by the flow.",
  "capability_summary": [
    "Short capability phrase 1",
    "Short capability phrase 2"
  ],
  "requirements": [
    {{
      "id": "CONTR-01",
      "candidate_text": "The system shall ...",
      "source_gold_requirement_id": "REQ-03",
      "source_gold_text": "The system shall ...",
      "intended_label": "not_fulfilled",
      "mutation_family": "missing_visible_step",
      "grounding_scope": "INDIRECT_FLOW_GROUNDED",
      "requirement_type": "FR",
      "ui_evaluability": "UI_VERIFIABLE",
      "non_evaluable_reason": "NONE",
      "visible_subtype": "STATE_CHANGE_ACROSS_SCREENS",
      "confidence": "MEDIUM",
      "generation_rationale": "Why this is a realistic close variant of the source gold requirement and why it may diversify later verification outcomes."
    }}
  ]
}}

Return a strong, de-duplicated, reviewable contrastive candidate set grounded in the accepted gold requirements, task, website, and domain.
""".strip()



# Compatibility wrapper for older hybrid-mode call sites.
def build_pure_prior_harvest_prompt(
    task: dict,
    selected_steps: list[int],
    flow_first_harvest: dict,
    retrieved_prior_entries: list[dict],
) -> str:
    confirmed_task = task.get("confirmed_task", "")
    website = task.get("website", "")
    domain = task.get("domain", "")
    flow_first_json = json.dumps(flow_first_harvest, indent=2, ensure_ascii=False)
    prior_json = json.dumps(retrieved_prior_entries, indent=2, ensure_ascii=False)

    return f"""
You are generating an enrichment pass for harvested software requirements from an ordered UI screenshot sequence.

Task description:
{confirmed_task}

Website:
{website}

Domain:
{domain}

The visible screenshots correspond to these REAL flow step indices:
{selected_steps}

Your role in this pass:
- Do NOT merely repeat the current harvested requirements.
- Use the screenshots as grounding evidence.
- Use the retrieved prior entries as a top-down prior only.
- Add complementary requirements only when they improve realism, breadth, and coverage.
- Prefer strong DIRECT_FLOW_GROUNDED or INDIRECT_FLOW_GROUNDED items over speculative additions.

Grounding scopes:
- DIRECT_FLOW_GROUNDED: clearly supported by the visible screenshots and their ordering
- INDIRECT_FLOW_GROUNDED: implied by visible UI cues, task context, or surrounding flow structure
- NEARBY_VARIANT: a disciplined close variant that remains tightly anchored to the visible feature space

Allowed values:
- grounding_scope: DIRECT_FLOW_GROUNDED | INDIRECT_FLOW_GROUNDED | NEARBY_VARIANT
- requirement_type: FR | NFR | UNCLEAR
- ui_evaluability: UI_VERIFIABLE | PARTIALLY_UI_VERIFIABLE | NOT_UI_VERIFIABLE
- task_relevance: HIGH | MEDIUM | LOW
- confidence: HIGH | MEDIUM | LOW

Here is the current harvested set:
{flow_first_json}

Here are the retrieved prior entries:
{prior_json}

Return ONLY valid JSON in this format:
{{
  "flow_overview": "Optional refined one-line description of the system or service represented by the flow.",
  "capability_summary": [
    "Short capability phrase 1",
    "Short capability phrase 2"
  ],
  "requirements": [
    {{
      "id": "HARV-PRIOR-01",
      "harvested_text": "The system shall ...",
      "grounding_scope": "INDIRECT_FLOW_GROUNDED",
      "requirement_type": "FR",
      "ui_evaluability": "PARTIALLY_UI_VERIFIABLE",
      "task_relevance": "MEDIUM",
      "evidence_steps": [5, 10],
      "confidence": "MEDIUM",
      "rationale": "Why this enrichment item is grounded in the visible flow and how it complements the current harvested set.",
      "visible_core_candidate": null
    }}
  ]
}}

Return only strong enrichment items that meaningfully complement the current harvested set.
""".strip()
