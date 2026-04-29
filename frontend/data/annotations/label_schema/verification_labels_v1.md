# Verification Label Schema

This file defines the label logic used for verification of requirements against ordered UI screenshot flows.

The schema is evidence-first but not unrealistically strict. A requirement is not considered fulfilled because it is plausible, common for the website, or implied by the task. A fulfilled decision requires visible UI evidence from the ordered flow. However, this project verifies the visible UI contract, not the full internal system truth. Routine backend or persistence behavior does not block `FULFILLED` when the expected UI outcome is visibly confirmed.

## 1. Motivation

Natural-language requirements are often ambiguous. Requirements Engineering research commonly discusses ambiguity, vagueness, generality, and context dependence as recurring quality problems in requirements documents. For this project, ambiguity is not only a property of the text. It can also arise when a clear requirement is mapped to incomplete visual evidence.

This project therefore separates two sources of uncertainty:

1. **Textual ambiguity**: the requirement itself is unclear.
2. **Evidence limitation**: the requirement may be clear, but the screenshot flow does not show enough evidence.

Both sources can block a `FULFILLED` decision.

The main verification target is the visible UI contract. Hidden system behavior is only treated as blocking when it is the central requirement claim or when no visible success proxy is shown.

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
- The system maintains a specific uptime ratio.

Hidden claims may have visible proxies, but a proxy is only sufficient when it clearly represents the expected UI-level success state.

### Visible success proxy

A visible success proxy is a UI state that represents the expected result of a hidden or backend-supported action.

Examples:

- A cart badge changes from `0` to `1`.
- A selected item appears in the cart.
- A page shows `Order confirmed`.
- A selected store card changes to `Home Store`.
- A user is redirected to an account dashboard after login.

A visible success proxy can support `FULFILLED` for UI-level requirements, even if the underlying database state or backend process is not directly observable.

### Routine system dependency

A routine system dependency is hidden system behavior that is necessary for implementation but is not the actual verification target.

Examples:

- Saving a selected value.
- Updating a cart count.
- Navigating to a logged-in page.
- Storing a temporary UI selection.

Routine system dependencies do not block `FULFILLED` if the visible UI outcome is fully shown.

### Nontrivial hidden property

A nontrivial hidden property is a system property that cannot be inferred from screenshots alone and is itself central to the requirement.

Examples:

- Security of authentication.
- Real payment processing.
- Email delivery.
- Long-term data persistence without visible confirmation.
- Uptime ratio.
- Ranking correctness by true geographic distance.
- Backend consistency across sessions.

Nontrivial hidden properties block `FULFILLED` unless additional evidence or a strong visible success proxy is available.

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
| `PARTIALLY_UI_VERIFIABLE` | The requirement has a visible UI core, but full satisfaction also depends on hidden state, persistence, external systems, data correctness, policy, timing, or business logic. |
| `NOT_UI_VERIFIABLE` | The requirement has no stable visible UI manifestation in the flow, or is too abstract for screenshot-based verification. |

UI evaluability is not the same as the verification label. It answers whether the requirement is suitable for screenshot-based verification. The verification label answers what the concrete flow shows.

## 4. Verification labels

### `FULFILLED`

Use `FULFILLED` only if all UI-observable core claims are visibly supported by the ordered screenshot flow.

Required conditions:

- At least one explicit evidence unit is recorded.
- All UI-observable core claims are supported.
- No UI-observable core claim is contradicted.
- No unresolved material uncertainty remains about the visible UI behavior.
- Hidden backend or persistence behavior is either outside the UI verification scope or represented by a visible success proxy.

Hidden implementation details do not block `FULFILLED` when the visible UI contract is satisfied.

Examples:

- A product is added to a cart and the cart count visibly changes.
- A login flow ends on a user account page.
- A selected store card visibly changes to `Home Store`.

Do not use `FULFILLED` when the flow only shows a button or form, but the requirement also requires a visible outcome and no outcome or success proxy is shown.

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
- A hidden system effect is required, but no visible success proxy is shown.

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
- The requirement depends on a nontrivial hidden property.
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
| `UNVERIFIED_SYSTEM_OUTCOME` | The requirement needs a visible or hidden outcome, but the flow only shows the mechanism and not the resulting success state. | Blocks `FULFILLED`; usually `PARTIALLY_FULFILLED`. |
| `NONTRIVIAL_HIDDEN_PROPERTY` | The requirement depends on a hidden property that cannot be validated from screenshots, such as security, uptime, email delivery, payment processing, ranking correctness, or long-term persistence without visible confirmation. | Blocks `FULFILLED`; usually `ABSTAIN`, or `PARTIALLY_FULFILLED` if a visible mechanism exists. |

Optional non-blocking notes can be stored separately:

| Note | Meaning |
| --- | --- |
| `ROUTINE_SYSTEM_DEPENDENCY` | The requirement relies on ordinary backend or persistence behavior, but the UI outcome is fully visible. This does not block `FULFILLED`. |
| `VISIBLE_SUCCESS_PROXY` | A hidden effect is represented by a visible confirmation, updated UI state, navigation result, displayed record, cart count, or similar success state. This can support `FULFILLED`. |

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
| `OUT_OF_SCOPE` | The claim refers to routine internal behavior that is not part of the visible UI verification target. |

The final label should be derived from claim statuses:

| Final label | Claim-level pattern |
| --- | --- |
| `FULFILLED` | All UI-observable core claims are `SUPPORTED`; no unresolved material uncertainty about visible UI behavior. Hidden routine dependencies may be `OUT_OF_SCOPE` if the visible success state is shown. |
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
    "UNVERIFIED_SYSTEM_OUTCOME"
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
  "evidence_note": "The button is visible, but the flow does not show a click result, confirmation, or updated home-store state."
}
```

A candidate's intended label is not a gold label. Intended labels are generation targets and must be reviewed manually.

For evaluation, every gold verification item must have:

- `verification_label`
- `ui_evaluability`
- evidence steps or an explicit insufficiency reason
- uncertainty reasons when the label is not `FULFILLED`
- optional non-blocking notes such as `ROUTINE_SYSTEM_DEPENDENCY` or `VISIBLE_SUCCESS_PROXY`
- a short rationale

If the repository keeps accepted product requirements and verification benchmark items separate, then accepted product requirements may remain in `requirements_gold/`, while final four-class verification labels should be stored in a separate `verification_gold/` layer.

## 8. Pipeline consistency gates

The pipeline should not rely only on prompting. It should validate model outputs with deterministic gates.

Suggested gates:

```text
FULFILLED:
  requires evidence
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

This makes the label logic testable. A verifier output that violates these gates should be rejected, downgraded, or sent to human review.

## 9. Research grounding

This schema combines three research-backed ideas:

1. **Ambiguity management in Requirements Engineering.** Natural-language requirements often suffer from ambiguity, vagueness, generality, and context dependence. This motivates explicit uncertainty reasons such as `TEXTUAL_AMBIGUITY`, `SCOPE_OR_CONTEXT_AMBIGUITY`, and `QUANTIFIER_OR_COMPLETENESS_AMBIGUITY`.
2. **Traceability and verification information.** Requirements should be connected to evidence and verification information. This motivates explicit evidence units such as step indices, visible UI states, transitions, and bounding boxes.
3. **Abstention under uncertainty.** A verifier should not be forced to predict `FULFILLED` or `NOT_FULFILLED` when the evidence is insufficient. This motivates `ABSTAIN` as a controlled non-decision.

GUI-specific uncertainty is handled separately from textual ambiguity. Categories such as `FLOW_COVERAGE_GAP`, `EVIDENCE_INTERPRETATION_AMBIGUITY`, `UNVERIFIED_SYSTEM_OUTCOME`, and `NONTRIVIAL_HIDDEN_PROPERTY` are specific to screenshot-based UI verification. They are supported by the practical limitations of GUI test automation and by recent GUI grounding work, where locating and interpreting screen elements is treated as a central task.

## 10. References

- Berry, D. M., Kamsties, E., and Krieger, M. M. (2003). *From Contract Drafting to Software Specification: Linguistic Sources of Ambiguity*. University of Waterloo Technical Report.  
  Used for: textual ambiguity, vague wording, quantifier ambiguity, and terms such as `all`, `each`, `every`, and `only`.

- Gervasi, V., Ferrari, A., Zowghi, D., and Spoletini, P. (2019). *Ambiguity in Requirements Engineering: Towards a Unifying Framework*. In *From Software Engineering to Formal Methods and Tools, and Back*, LNCS 11865, pp. 191–210. DOI: 10.1007/978-3-030-30985-5_12.  
  Used for: treating ambiguity as a recurring Requirement Engineering problem and not only as a simple writing defect.

- Hendrickx, K., Perini, L., Van der Plas, D., Meert, W., and Davis, J. (2024). *Machine Learning with a Reject Option: A Survey*. *Machine Learning*, 113, 3073–3110. DOI: 10.1007/s10994-024-06534-x.  
  Used for: justifying `ABSTAIN` as a controlled non-decision when a prediction would be unreliable.
