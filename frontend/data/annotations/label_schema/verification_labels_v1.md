    # Verification Label Schema v1

This file defines the label logic used for manual verification of candidate requirements against ordered UI screenshot flows.

The schema is intentionally conservative. A requirement is not considered fulfilled because it is plausible, common for the website, or implied by the task. A fulfilled decision requires visible UI evidence from the ordered flow.

## 1. Motivation

Natural-language requirements are often ambiguous. Requirements Engineering research commonly discusses ambiguity, vagueness, generality, and context dependence as recurring quality problems in requirements documents. For this project, ambiguity is not only a property of the text. It can also arise when a clear requirement is mapped to incomplete visual evidence.

This project therefore separates two sources of uncertainty:

1. **Textual ambiguity**: the requirement itself is unclear.
2. **Evidence limitation**: the requirement may be clear, but the screenshot flow does not show enough evidence.

Both sources can block a `FULFILLED` decision.

This is consistent with the evidence-first goal of the thesis: a verifier should only mark a requirement as fulfilled when it can point to concrete screen-level evidence, such as screenshot ids, visible text, UI state, transitions, or bounding boxes.

## 2. Core concepts

### Requirement claim

A requirement claim is a single checkable statement inside a requirement.

Example:

> The system shall allow users to set the closest store as their home store.

Possible claims:

- A store search result is shown.
- A control for setting a store as home store is shown.
- The selected store becomes the home store.
- The resulting home-store state is visibly confirmed or persisted.

Many requirements contain several claims. Labels should be assigned after identifying the important claims.

### Observable claim

An observable claim can be checked from the screenshot flow.

Example:

> The result card shows a `SET AS HOME STORE` button.

### Hidden claim

A hidden claim cannot be directly checked from screenshots.

Examples:

- The store is persisted in the user profile.
- A confirmation email is sent.
- A payment was processed securely.
- The list is sorted by true geographic distance.

Hidden claims may have visible proxies, but a proxy is only sufficient when it clearly confirms the claim.

### Evidence unit

An evidence unit is the smallest UI observation that supports or contradicts a claim.

Allowed evidence units include:

- `step_index`
- visible text
- visible UI state
- transition between two steps
- screenshot region or bounding box
- short evidence note

## 3. UI evaluability

UI evaluability describes whether a requirement can in principle be assessed from the visible screenshot flow.

| Label | Definition |
| --- | --- |
| `UI_VERIFIABLE` | The relevant claims can be checked from visible UI evidence in the screenshot flow. |
| `PARTIALLY_UI_VERIFIABLE` | The requirement has a visible UI core, but full satisfaction depends on hidden state, persistence, external systems, data correctness, policy, timing, or business logic. |
| `NOT_UI_VERIFIABLE` | The requirement has no stable visible UI manifestation in the flow, or is too abstract for screenshot-based verification. |

UI evaluability is not the same as the verification label. It answers whether the requirement is suitable for screenshot-based verification. The verification label answers what the concrete flow shows.

## 4. Verification labels

### `FULFILLED`

Use `FULFILLED` only if all UI-observable core claims are visibly supported by the ordered screenshot flow.

Required conditions:

- At least one explicit evidence unit is recorded.
- All observable core claims are supported.
- No observable core claim is contradicted.
- No material uncertainty remains that could change the decision.

Do not use `FULFILLED` when the flow only shows a button but not the required outcome, or when the result depends on hidden backend state.

### `PARTIALLY_FULFILLED`

Use `PARTIALLY_FULFILLED` if the flow supports a meaningful visible part of the requirement, but full satisfaction is not established.

Required conditions:

- At least one important claim is supported.
- At least one important claim is missing, hidden, ambiguous, or only weakly evidenced.
- No core claim is clearly contradicted.

Typical cases:

- Mechanism visible, outcome hidden.
- Input visible, resulting state unclear.
- Navigation visible, final confirmation missing.
- Some required information visible, other required information missing.

Example:

> A `SET AS HOME STORE` button is visible, but no confirmation or persisted home-store state is shown.

### `NOT_FULFILLED`

Use `NOT_FULFILLED` only if visible UI evidence contradicts the requirement.

Required conditions:

- At least one core claim is contradicted by visible evidence.
- The contradiction is tied to a step, visible state, text, transition, or region.
- The decision does not rely only on missing evidence.

Important rule:

> Missing evidence is not automatically counter-evidence.

Example:

> A requirement says the selected store should become the home store, but after the relevant search the UI still marks a different store as `Home Store` and all relevant searched stores still show `SET AS HOME STORE`.

### `ABSTAIN`

Use `ABSTAIN` if the available screenshots do not allow a reliable positive or negative decision.

Typical cases:

- The relevant screen is missing.
- The required before/after transition is missing.
- The requirement depends on backend state or an external system.
- The text is too ambiguous to decompose into stable claims.
- The visible evidence could support multiple incompatible interpretations.
- The screenshot region is unreadable or cropped.

`ABSTAIN` is not a failure label. It is a controlled non-decision.

## 5. Sources of material uncertainty

Use a small set of uncertainty reasons. These are not additional verification labels. They explain why a decision is not fully supported.

| Reason | Definition | Typical effect |
| --- | --- | --- |
| `TEXTUAL_AMBIGUITY` | The requirement wording itself allows multiple interpretations or uses vague/general terms such as clear, easy, relevant, proper, or appropriate. | Usually rewrite before gold annotation, otherwise `ABSTAIN`. |
| `SCOPE_OR_CONTEXT_AMBIGUITY` | It is unclear which screen, item, user role, flow segment, or system behavior is in scope. | `ABSTAIN` unless a stable observable core remains. |
| `QUANTIFIER_OR_COMPLETENESS_AMBIGUITY` | The requirement uses strong terms such as all, each, every, only, always, or closest, but the flow only shows partial evidence. | Avoid `FULFILLED` unless completeness is visibly established. |
| `EVIDENCE_INTERPRETATION_AMBIGUITY` | Relevant UI evidence is visible, but its meaning, selected state, or causal relation to the action is unclear. | `PARTIALLY_FULFILLED` if a meaningful core is supported, otherwise `ABSTAIN`. |
| `FLOW_COVERAGE_GAP` | The screenshot sequence does not include the step before, during, or after the relevant behavior. | `PARTIALLY_FULFILLED` if a visible core exists, otherwise `ABSTAIN`. |
| `NON_VISIBLE_SYSTEM_DEPENDENCY` | Full satisfaction depends on persistence, backend state, external systems, security, payment processing, email delivery, hidden policy, or hidden data correctness. | Usually `PARTIALLY_FULFILLED` or `ABSTAIN`. |

Optional evidence-quality flags can be stored separately:

| Flag | Meaning |
| --- | --- |
| `LOW_VISUAL_QUALITY` | The relevant region is blurred, downscaled, cropped, occluded, or unreadable. |
| `MISSING_REGION` | The relevant UI region is outside the screenshot viewport. |

## 6. Claim evidence statuses

Each important claim can receive one status.

| Status | Meaning |
| --- | --- |
| `SUPPORTED` | Visible evidence supports the claim. |
| `CONTRADICTED` | Visible evidence contradicts the claim. |
| `MISSING` | The claim could be visible in principle, but the flow does not show enough evidence. |
| `HIDDEN` | The claim depends on non-visible system behavior. |
| `AMBIGUOUS` | The evidence exists, but its meaning is not stable enough for a clear decision. |

The final label should be derived from claim statuses:

| Final label | Claim-level pattern |
| --- | --- |
| `FULFILLED` | All observable core claims are `SUPPORTED`; no material uncertainty. |
| `PARTIALLY_FULFILLED` | At least one important claim is `SUPPORTED`, and at least one important claim is `MISSING`, `HIDDEN`, or `AMBIGUOUS`. |
| `NOT_FULFILLED` | At least one observable core claim is `CONTRADICTED`. |
| `ABSTAIN` | There is not enough support or contradiction to decide. |

## 7. Manual promotion from candidate to gold

When a candidate requirement is promoted into a gold verification item, the following fields must be added or confirmed:

```json
{
  "requirement_id": "REQ-05",
  "source": "candidate",
  "review_status": "accepted",
  "ui_evaluability": "PARTIALLY_UI_VERIFIABLE",
  "verification_label": "PARTIALLY_FULFILLED",
  "uncertainty_reasons": [
    "FLOW_COVERAGE_GAP",
    "NON_VISIBLE_SYSTEM_DEPENDENCY"
  ],
  "claims": [
    {
      "claim": "A control for setting a store as home store is visible.",
      "status": "SUPPORTED",
      "evidence_steps": [4]
    },
    {
      "claim": "The selected store is visibly confirmed as home store.",
      "status": "MISSING",
      "evidence_steps": []
    }
  ],
  "evidence_note": "The button is visible, but the flow does not show a click result, confirmation, or persisted state."
}
```

A candidate's intended label is not a gold label. Intended labels are generation targets and must be reviewed manually.

For evaluation, every gold verification item must have:

- `verification_label`
- `ui_evaluability`
- evidence steps or an explicit insufficiency reason
- uncertainty reasons when the label is not `FULFILLED`
- a short rationale

If the repository keeps accepted product requirements and verification benchmark items separate, then accepted product requirements may remain in `requirements_gold/`, while final four-class verification labels should be stored in a separate `verification_gold/` layer.

## 8. Pipeline consistency gates

The pipeline should not rely only on prompting. It should validate model outputs with deterministic gates.

Suggested gates:

```text
FULFILLED:
  requires evidence
  requires all observable core claims SUPPORTED
  forbids CONTRADICTED core claims
  forbids material uncertainty

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

This makes the label logic testable. A verifier output that violates these gates should be rejected, downgraded, or sent to human review.

## 9. References

- Berry, D. M., Kamsties, E., and Krieger, M. M. *From Contract Drafting to Software Specification: Linguistic Sources of Ambiguity*. Technical report, University of Waterloo, 2003.
- Gervasi, V., et al. *Ambiguity in Requirements Engineering: towards a unifying framework*. 2019.
- Kiyavitskaya, N., et al. *Requirements for Tools for Ambiguity Identification and Measurement in Natural Language Requirements Specifications*. WER 2007.
- ISO/IEC/IEEE 29148:2018. *Systems and software engineering — Life cycle processes — Requirements engineering*.
- Nass, M., Alégroth, E., and Feldt, R. *Why many challenges with GUI test automation (will) remain*. Information and Software Technology, 2021.
- Hendrickx, K., et al. *Machine Learning with a Reject Option: A survey*. Machine Learning, 2024.
- Cheng, K., et al. *SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents*. ACL 2024.
