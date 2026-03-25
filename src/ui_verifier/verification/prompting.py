from __future__ import annotations


def build_verification_prompt(task: dict, requirement_text: str, selected_steps: list[int]) -> str:
    confirmed_task = task.get("confirmed_task", "")
    website = task.get("website", "")
    domain = task.get("domain", "")

    return f"""
You are given an ordered screenshot sequence of a web UI flow and one candidate software requirement.

Task description:
{confirmed_task}

Website:
{website}

Domain:
{domain}

Requirement to verify:
{requirement_text}

The visible screenshots correspond to these REAL flow step indices:
{selected_steps}

Important:
- The values in evidence[*].step_index MUST use the real flow step indices listed above.
- Do NOT renumber the screenshots as 1, 2, 3, ...
- Only use evidence that is directly supported by the visible screenshots.
- If the screenshots do not provide enough evidence, return "abstain".
- Only return "fulfilled" if there is explicit supporting evidence.
- For "fulfilled" and "partially_fulfilled", include at least one evidence item.
- For "not_fulfilled" or "abstain", evidence may be empty.

Return ONLY valid JSON in this format:
{{
  "label": "fulfilled | partially_fulfilled | not_fulfilled | abstain",
  "evidence": [
    {{
      "step_index": 1,
      "reason": "Short explanation of the supporting UI evidence"
    }}
  ],
  "confidence": 0.0,
  "explanation": "Short explanation of the decision"
}}
""".strip()
