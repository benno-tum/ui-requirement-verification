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
They are broader requirement hypotheses that will later be normalized into candidate verification items.

PURE-inspired prior you must respect:
- In realistic requirements sets, many requirements are NOT fully UI-verifiable from screenshots alone.
- Many others are only PARTIALLY_UI_VERIFIABLE because they contain a visible core plus hidden-state aspects.
- Requirement sets are not dominated by tiny field-level widget claims.
- They often include broader workflow requirements and NFR-like expectations such as clarity, transparency, consistency, guidance, feedback, and configurability.
- Therefore, do NOT collapse everything into tiny directly visible widget claims.
- Treat screenshots as grounding evidence for broader product or workflow requirements, not merely as an inventory of visible controls.
- Prefer broader, requirement-like statements when the screenshots support them.
- Use PARTIALLY_UI_VERIFIABLE and NOT_UI_VERIFIABLE when that is the better classification.
- If a broader requirement has a visible UI-observable core, keep the broader harvested_text and also provide a visible_core_candidate.

Goal:
Produce requirement-like hypotheses that are useful for a later evidence-first UI verification benchmark and closer to the kind of broader requirements seen in PURE.

Coverage target:
When the flow reasonably supports it, aim for a mixed harvested set that includes:
1. broader workflow or task-support requirements
2. directly UI-verifiable visible requirements
3. partially UI-verifiable requirements with a visible core
4. NFR-like visible requirements about guidance, clarity, transparency, consistency, or feedback
5. occasionally a broader requirement that is mostly not UI-verifiable but still plausibly suggested by the flow

Strong preference order:
1. broader workflow or task-support requirements
2. task-level visible outcomes
3. navigation outcomes across screens
4. visible state changes across screens
5. validation / feedback / confirmation behavior
6. visible content updates
7. only then isolated control-presence claims

Avoid bad low-value items unless they are clearly task-critical:
- "The system shall display a first name field"
- "The system shall display a last name field"
- "The system shall display a confirmation number field"
- generic button or field presence with no broader verification value
- harvested items that simply restate one entered value from the task instance

Before emitting a local widget requirement, ask:
- Can this be merged into a broader requirement about the task step?
- Is this a visible manifestation of a broader requirement?
- Is this genuinely useful as a benchmark item?
- Would this still be a sensible requirement if the exact field label or example value changed?

Good examples of broader formulations:
- "The system shall collect pickup details including location, date, and time."
- "The system shall carry previously selected rental details forward into later checkout steps."
- "The system shall allow the user to configure optional add-ons and reflect those choices in the UI."
- "The system shall provide visible progress feedback across the booking flow."
- "The system shall support discoverability of events through search and filtering."
- "The system shall provide transparent comparison information for plan or ticket options."
- "The system shall maintain consistency between selected filter criteria and displayed results."

Examples of acceptable NFR-like harvested hypotheses when grounded in the UI:
- "The system shall provide clear progress guidance during checkout."
- "The system shall present pricing and option details transparently enough for comparison."
- "The system shall provide visible feedback when a filter or configuration choice becomes active."
- "The system shall keep user-selected context consistent across subsequent screens."

Rules:
- Generate software requirements, not user goals, not test instructions, not business objectives.
- Use declarative requirement style such as "The system shall ..."
- Prefer singular but meaningful items. Merging closely related widget-level observations is encouraged.
- Use screenshots plus task context, but do not invent hidden backend behavior as visible fact.
- The harvested_text should usually be broader than the exact visible widget state.
- The screenshots should lightly anchor the requirement, not shrink it into a literal UI description.
- If something suggests a broader requirement whose full satisfaction depends on hidden state, classify it as PARTIALLY_UI_VERIFIABLE or NOT_UI_VERIFIABLE as appropriate.
- If evidence is weak, omit the item or lower confidence.
- It is acceptable to return fewer items if only a few strong items are supported.

Classification guidance:
- UI_VERIFIABLE:
  fully judgeable from ordered screenshots alone
- PARTIALLY_UI_VERIFIABLE:
  visible core exists, but full satisfaction also depends on hidden state, external delivery, full coverage, performance, policy, or broader context
- NOT_UI_VERIFIABLE:
  mainly backend, timing, security, architecture, hidden data correctness, or too abstract for screenshot-based judgment

Taxonomy values:
- requirement_type: FR | NFR | UNCLEAR
- ui_evaluability: UI_VERIFIABLE | PARTIALLY_UI_VERIFIABLE | NOT_UI_VERIFIABLE
- non_evaluable_reason: NONE | BACKEND_HIDDEN_STATE | PERFORMANCE_TIMING | SECURITY_PRIVACY | EXTERNAL_INTEGRATION | TOO_ABSTRACT | BUSINESS_RULE_NOT_VISIBLE | DATA_CORRECTNESS_NOT_VISIBLE
- visible_subtype: NONE | TEXT_OR_ELEMENT_PRESENCE | NAVIGATION_OUTCOME | STATE_CHANGE_ACROSS_SCREENS | VALIDATION_OR_FEEDBACK | CONTENT_UPDATE | LAYOUT_POSITION
- task_relevance: HIGH | MEDIUM | LOW
- confidence: HIGH | MEDIUM | LOW

Important output requirements:
- Do not force all items to be UI_VERIFIABLE.
- Do not force all items to be FR.
- Do not force a minimum number of items.
- Return a balanced set of strong hypotheses when supported.
- Prefer fewer, broader, more benchmark-useful items over many tiny local ones.
- If defensible from the flow, include at least one broader workflow requirement.
- If defensible from the flow, include at least one PARTIALLY_UI_VERIFIABLE requirement.
- If defensible from the flow, include at least one NFR-like requirement.
- For PARTIALLY_UI_VERIFIABLE items, visible_core_candidate should usually be non-null.
- For NOT_UI_VERIFIABLE items, visible_subtype must be NONE.

Return ONLY valid JSON in this format:
{{
  "requirements": [
    {{
      "id": "HARV-01",
      "harvested_text": "The system shall ...",
      "requirement_type": "FR",
      "ui_evaluability": "PARTIALLY_UI_VERIFIABLE",
      "non_evaluable_reason": "EXTERNAL_INTEGRATION",
      "visible_subtype": "VALIDATION_OR_FEEDBACK",
      "task_relevance": "HIGH",
      "evidence_steps": [5, 10],
      "confidence": "MEDIUM",
      "rationale": "Why this hypothesis is supported by visible evidence and why it is only partially UI-verifiable.",
      "visible_core_candidate": "The system shall display visible confirmation feedback after the user submits the form."
    }}
  ]
}}

Return only strong, non-trivial items supported by the screenshots.
""".strip()



def build_candidate_rewrite_prompt(harvest_payload: dict) -> str:
    harvest_json = json.dumps(harvest_payload, indent=2, ensure_ascii=False)

    return f"""
You are given harvested requirement hypotheses extracted from an ordered UI screenshot flow.

Your task is to rewrite them into candidate requirements for a UI verification benchmark.

Goal:
Produce reviewable candidate requirements that are useful for later evidence-first verification.

Important principles:
- Candidate requirements are narrower and more verification-oriented than harvested requirements.
- However, do NOT create trivial field-by-field items unless they are independently meaningful.
- Merge low-value local observations into one broader candidate when they belong to the same visible UI function.
- Preserve the original semantic intent of the harvested item.
- Prefer visible, reviewable verification units.
- If the harvested item is only partially UI-verifiable, rewrite it to its visible core when that produces a good candidate.
- Drop weak, redundant, overly speculative, or purely task-instance-specific items.

What makes a good candidate requirement:
- It is meaningful as a verification unit.
- It can be reviewed by a human annotator.
- It is not just a restatement of a single filled value from one screenshot.
- It has a clear visible manifestation in one screen or across a short ordered sequence.
- It avoids hidden backend claims unless the visible core is explicitly extracted.

Rewrite policy:
1. Keep strong broader items when they remain reviewable.
2. Rewrite partially UI-verifiable harvested items into visible-core candidates when appropriate.
3. Merge repetitive local field items into one candidate.
4. Remove duplicates and near-duplicates.
5. Remove claims that depend too strongly on example-specific data values.
6. Prefer requirements about:
   - navigation outcomes
   - state carry-over
   - visible feedback
   - visible selection/configuration options
   - grouped information collection
7. Avoid trivial candidates such as:
   - The system shall display a first name field.
   - The system shall display a last name field.
   - The system shall display an email field.
   unless no better grouped candidate exists.

Output requirements:
- Keep source_harvest_id.
- Assign a candidate id like REQ-01.
- Keep or refine requirement_type, ui_evaluability, and visible_subtype.
- Use benchmark_decision = DIRECT_INCLUDE, REWRITE_TO_VISIBLE_CORE, or EXCLUDE_FROM_VERIFICATION_BENCHMARK.
- Use candidate_origin = DIRECT_FROM_HARVEST or VISIBLE_CORE_REWRITE.
- Add normalization_notes explaining the rewrite decision.

Return ONLY valid JSON in this format:
{{
  "requirements": [
    {{
      "id": "REQ-01",
      "source_harvest_id": "HARV-01",
      "candidate_text": "The system shall collect purchaser contact information including name, email address, and postal code.",
      "requirement_type": "FR",
      "ui_evaluability": "UI_VERIFIABLE",
      "visible_subtype": "TEXT_OR_ELEMENT_PRESENCE",
      "benchmark_decision": "DIRECT_INCLUDE",
      "candidate_origin": "DIRECT_FROM_HARVEST",
      "normalization_notes": "Merged multiple local form-field observations into one reviewable candidate."
    }}
  ]
}}

Here are the harvested requirements:
{harvest_json}

Return only strong, de-duplicated, benchmark-useful candidate requirements.
""".strip()



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
- Do NOT merely repeat the flow-first harvested requirements.
- Use the screenshots as grounding evidence.
- Use the PURE-inspired prior entries as a top-down requirement prior.
- Generate additional requirement hypotheses that improve realism, breadth, and coverage.

What to add if defensible from the flow:
1. broader workflow or task-support requirements
2. NFR-like requirements about clarity, transparency, guidance, feedback, or consistency
3. partially UI-verifiable requirements with a visible core
4. occasionally a broader requirement that is mostly not UI-verifiable but plausibly suggested by the flow

Important:
- Prefer requirements that complement the flow-first set instead of duplicating it.
- It is acceptable to output zero to a few items if no strong enrichment items are supported.
- The harvested_text may be broader than the visible widget state.
- If the requirement is only partly visible, mark it PARTIALLY_UI_VERIFIABLE and provide a visible_core_candidate.
- If it is mostly not screenshot-verifiable, mark it NOT_UI_VERIFIABLE and set visible_subtype to NONE.

Taxonomy values:
- requirement_type: FR | NFR | UNCLEAR
- ui_evaluability: UI_VERIFIABLE | PARTIALLY_UI_VERIFIABLE | NOT_UI_VERIFIABLE
- non_evaluable_reason: NONE | BACKEND_HIDDEN_STATE | PERFORMANCE_TIMING | SECURITY_PRIVACY | EXTERNAL_INTEGRATION | TOO_ABSTRACT | BUSINESS_RULE_NOT_VISIBLE | DATA_CORRECTNESS_NOT_VISIBLE
- visible_subtype: NONE | TEXT_OR_ELEMENT_PRESENCE | NAVIGATION_OUTCOME | STATE_CHANGE_ACROSS_SCREENS | VALIDATION_OR_FEEDBACK | CONTENT_UPDATE | LAYOUT_POSITION
- task_relevance: HIGH | MEDIUM | LOW
- confidence: HIGH | MEDIUM | LOW

Here is the current flow-first harvested set:
{flow_first_json}

Here are the retrieved PURE-inspired prior entries:
{prior_json}

Return ONLY valid JSON in this format:
{{
  "requirements": [
    {{
      "id": "HARV-PURE-01",
      "harvested_text": "The system shall ...",
      "requirement_type": "NFR",
      "ui_evaluability": "PARTIALLY_UI_VERIFIABLE",
      "non_evaluable_reason": "DATA_CORRECTNESS_NOT_VISIBLE",
      "visible_subtype": "CONTENT_UPDATE",
      "task_relevance": "MEDIUM",
      "evidence_steps": [5, 11, 12],
      "confidence": "MEDIUM",
      "rationale": "Why this enrichment item is grounded in the screenshots and how it complements the flow-first set.",
      "visible_core_candidate": "The system shall visibly indicate which filter criteria are currently active."
    }}
  ]
}}

Return only strong enrichment items that meaningfully complement the flow-first set.
""".strip()
