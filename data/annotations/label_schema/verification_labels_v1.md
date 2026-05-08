# Verification Label Schema v1

This project verifies textual requirements against ordered UI screenshot flows. The verifier judges the visible UI contract first. Routine backend or persistence behavior does not block `FULFILLED` when the visible UI outcome is shown. Nontrivial hidden properties must not be inferred from screenshots alone.

## Core terms

- `requirement claim`: one checkable semantic statement decomposed from the requirement text itself.
- `observable claim`: a claim that can be checked from the screenshot flow.
- `hidden claim`: a claim that depends on non-visible state or system behavior.
- `visible success proxy`: a visible UI state that stands in for a routine hidden effect, such as a cart badge change, confirmation state, selected item appearing, or redirect to a dashboard.
- `routine system dependency`: ordinary hidden support behavior behind a visible UI outcome. This is non-blocking when the expected UI state is shown.
- `nontrivial hidden property`: a central hidden property that screenshots cannot verify, such as security, uptime, real payment processing, email delivery, ranking correctness, or long-term data correctness without visible confirmation.
- `evidence unit`: the smallest recorded UI observation. Typical units are a `step_index`, visible text, a visible state change, a transition across steps, or a screenshot region.

## Requirement Claim Text Discipline

Atomic requirement claims are decomposition artifacts, not evidence summaries. They must be written from the requirement only, before considering the screenshot flow. A claim may later receive an evidence status, but the claim text itself must not describe what the UI, screenshot, page, field, button, selector, or user-entered value happens to show.

Claim text should:

- preserve only the semantic obligations in the requirement
- split conjunctions, conditions, outcomes, and hidden effects into smaller checkable statements
- avoid adding concrete values or UI elements that appear only in the task flow or screenshots
- avoid words such as `UI`, `screenshot`, `screen`, `visible`, `field`, `button`, `dropdown`, `selector`, `page`, `panel`, or `the user-entered ...` unless that wording is already part of the requirement

Evidence-specific details belong in `evidence_units`, `evidence_note`, or `rationale`, not in `claims`.

Example:

Requirement: `The system shall allow applicants to filter job openings by department.`

Good claim: `The system supports filtering job openings by department.`

Bad claim: `Selecting MBTA - Safety narrows the visible results to safety department postings.`

## UI evaluability

| Label | Meaning |
| --- | --- |
| `UI_VERIFIABLE` | The relevant claims can be checked from visible UI evidence. |
| `PARTIALLY_UI_VERIFIABLE` | The requirement has a visible UI core, but full satisfaction also depends on hidden state, external systems, persistence, policy, or business logic. |
| `NOT_UI_VERIFIABLE` | The requirement has no stable visible UI manifestation in the flow, or is too abstract for screenshot-based verification. |

UI evaluability answers whether the requirement can be judged from UI evidence at all. It is separate from the final verification label.

## Verification labels

| Label | Use when |
| --- | --- |
| `FULFILLED` | All UI-observable core claims are visibly supported, no observable core claim is contradicted, at least one evidence unit is recorded, and no material uncertainty remains about visible UI behavior. |
| `PARTIALLY_FULFILLED` | At least one important claim is supported, and at least one important claim is still missing, hidden, or ambiguous. |
| `NOT_FULFILLED` | At least one observable core claim is contradicted by visible counter-evidence. Missing evidence alone is not enough. |
| `ABSTAIN` | The screenshots do not support a reliable positive or negative decision. |

For `FULFILLED`, `ROUTINE_SYSTEM_DEPENDENCY` and `VISIBLE_SUCCESS_PROXY` are allowed as non-blocking notes. `UNVERIFIED_SYSTEM_OUTCOME` and `NONTRIVIAL_HIDDEN_PROPERTY` block `FULFILLED`.

## Uncertainty reasons

| Reason | Meaning |
| --- | --- |
| `TEXTUAL_AMBIGUITY` | The requirement wording itself is unclear or vague. |
| `SCOPE_OR_CONTEXT_AMBIGUITY` | The relevant screen, item, role, or flow segment is unclear. |
| `QUANTIFIER_OR_COMPLETENESS_AMBIGUITY` | Terms like `all`, `each`, `only`, `always`, or `closest` are not visibly settled. |
| `EVIDENCE_INTERPRETATION_AMBIGUITY` | The UI evidence is visible, but its meaning or causal interpretation is unclear. |
| `FLOW_COVERAGE_GAP` | The necessary before/during/after step is missing from the screenshot sequence. |
| `UNVERIFIED_SYSTEM_OUTCOME` | The mechanism is shown, but the required success outcome is not. |
| `NONTRIVIAL_HIDDEN_PROPERTY` | The requirement depends on a hidden property screenshots cannot verify. |

Optional non-blocking notes:

- `ROUTINE_SYSTEM_DEPENDENCY`
- `VISIBLE_SUCCESS_PROXY`

## Claim evidence statuses

| Status | Meaning |
| --- | --- |
| `SUPPORTED` | Visible evidence supports the claim. |
| `CONTRADICTED` | Visible evidence contradicts the claim. |
| `MISSING` | The claim could be visible in principle, but the flow does not show enough evidence. |
| `HIDDEN` | The claim depends on non-visible system behavior. |
| `AMBIGUOUS` | The evidence exists, but its interpretation is unstable. |
| `OUT_OF_SCOPE` | The claim is a routine internal effect outside the visible UI verification target. |

## Manual promotion from candidate to gold

`requirements_candidate/.../candidate_requirements.json` may contain an `intended_label` generation target. That value is never gold by itself.

`verification_gold/<flow_id>/verification_gold.json` stores final human-reviewed benchmark items. Each item should preserve the source requirement text, ids, flow links, UI evaluability, visible subtype, and annotation notes. A promoted or migrated draft should record:

- final `verification_label`
- `ui_evaluability`
- `claims`
- `evidence_steps` and/or richer evidence units
- `uncertainty_reasons` when needed
- `evidence_note`
- `rationale`
- `review_status`

Existing `manual_verification_label` values from `requirements_gold` may be copied only as an initial draft label. Items still stay `needs_review` until the verification fields are actually completed.

## Pipeline consistency gates

Deterministic validation should reject or flag inconsistent labels:

```text
FULFILLED:
  requires at least one evidence unit
  requires all UI-observable core claims SUPPORTED
  forbids CONTRADICTED observable core claims
  forbids unresolved material uncertainty about visible UI behavior
  allows ROUTINE_SYSTEM_DEPENDENCY when the visible UI outcome is shown
  allows VISIBLE_SUCCESS_PROXY as support for hidden routine effects
  forbids UNVERIFIED_SYSTEM_OUTCOME
  forbids NONTRIVIAL_HIDDEN_PROPERTY as an unsupported core claim

PARTIALLY_FULFILLED:
  requires at least one SUPPORTED important claim
  requires at least one MISSING, HIDDEN, or AMBIGUOUS important claim
  forbids CONTRADICTED core claims

NOT_FULFILLED:
  requires at least one CONTRADICTED core claim
  requires visible counter-evidence

ABSTAIN:
  requires an insufficiency reason
  does not require positive evidence
```

## Compact references

- Berry, Kamsties, Krieger (2003): linguistic ambiguity in requirements.
- Gervasi, Ferrari, Zowghi, Spoletini (2019): ambiguity as a recurring RE problem.
- Hendrickx et al. (2024): abstention and reject-option reasoning under uncertainty.
