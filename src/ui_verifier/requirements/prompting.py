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
Generate candidate SOFTWARE REQUIREMENTS for the UI.

Important:
- Generate UI software requirements, not user goals, not test steps, and not business objectives.
- Only use requirements that are supported by the visible screenshots.
- Focus on observable UI behavior and UI state.
- Use the form: "The system shall ..."
- Keep each requirement singular and concrete.
- Do not invent hidden backend behavior.
- If evidence is weak, either omit the requirement or lower confidence.

Good examples:
- The system shall provide an input field for pickup location.
- The system shall display available truck options with price information after search.
- The system shall allow the user to choose a pickup location from a list of available locations.
- If the same return location option is selected, the system shall allow the user to continue without entering a separate return location before results are shown.

Bad examples:
- The user shall rent the cheapest truck.
- The system shall maximize business revenue.
- The system shall use an efficient database.

Return ONLY valid JSON in this format:
{{
  "requirements": [
    {{
      "id": "REQ-01",
      "type": "ui_element_value | workflow_transition | conditional_behavior",
      "text": "The system shall ...",
      "evidence_steps": [1, 5],
      "confidence": "high | medium | low"
    }}
  ]
}}

Return 5 to 12 requirements if possible.
""".strip()
