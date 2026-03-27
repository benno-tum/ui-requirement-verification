from __future__ import annotations


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
- Example:
  - if the visible screenshots are from steps [1, 5, 10, 14]
  - then valid evidence_steps are values like [1], [5, 10], or [14]
  - and invalid evidence_steps are values like [2], [3], or [4] unless those are real flow step indices listed above

Your job:
Generate harvested requirement hypotheses from the visible UI flow.
These are not final benchmark items yet.
For each item, classify whether it is UI_VERIFIABLE, PARTIALLY_UI_VERIFIABLE, or NOT_UI_VERIFIABLE from ordered screenshot evidence.
If a broader requirement is only partially visible, propose a narrower visible-core rewrite.

Important:
- Generate UI-facing software requirements, not user goals, not test steps, and not business objectives.
- Only use hypotheses that are supported by the visible screenshots.
- Focus on observable UI behavior and UI state.
- Use the form: "The system shall ..." or an equally requirement-like declarative formulation.
- Keep each requirement singular and concrete.
- Do not invent hidden backend behavior.
- If evidence is weak, either omit the requirement or lower confidence.

Rules:
- Prefer high-value UI claims that are relevant to the task and visible state changes.
- Do not include generic decorative page chrome unless it is important for the task or navigation outcome.
- Do not invent hidden backend, architecture, logging, persistence, performance, or external delivery behavior.
- If the broader requirement is only partially visible, keep the broader harvested_text but also provide a visible_core_candidate.
- It is acceptable to return fewer items if only a few strong items are supported.
- Do not force 5 to 12 items.

Taxonomy values:
- requirement_type: FR | NFR | UNCLEAR
- ui_evaluability: UI_VERIFIABLE | PARTIALLY_UI_VERIFIABLE | NOT_UI_VERIFIABLE
- non_evaluable_reason: NONE | BACKEND_HIDDEN_STATE | PERFORMANCE_TIMING | SECURITY_PRIVACY | EXTERNAL_INTEGRATION | TOO_ABSTRACT | BUSINESS_RULE_NOT_VISIBLE | DATA_CORRECTNESS_NOT_VISIBLE
- visible_subtype: NONE | TEXT_OR_ELEMENT_PRESENCE | NAVIGATION_OUTCOME | STATE_CHANGE_ACROSS_SCREENS | VALIDATION_OR_FEEDBACK | CONTENT_UPDATE | LAYOUT_POSITION
- task_relevance: HIGH | MEDIUM | LOW
- confidence: HIGH | MEDIUM | LOW

Return ONLY valid JSON in this format:
{{
  "requirements": [
    {{
      "id": "HARV-01",
      "harvested_text": "The system shall ...",
      "requirement_type": "FR",
      "ui_evaluability": "UI_VERIFIABLE",
      "non_evaluable_reason": "NONE",
      "visible_subtype": "TEXT_OR_ELEMENT_PRESENCE",
      "task_relevance": "HIGH",
      "evidence_steps": [1, 5],
      "confidence": "HIGH",
      "rationale": "Why this hypothesis is supported by visible evidence.",
      "visible_core_candidate": null
    }}
  ]
}}

Return only strong, non-trivial items supported by the screenshots.
""".strip()
