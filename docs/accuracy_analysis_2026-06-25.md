# Verification Accuracy Analysis — 2026-06-25

## Executive Summary

The lowest observed agreement scores do not have one common cause:

1. **Flow 09 improved from the invalid reported 30% to 50.0% in a clean Gemini V4 run.** The original file used `verifier=deterministic`; the replacement used 30 Gemini calls with zero fallbacks or failures.
2. **Flow 06 improved from 50.0% to 63.6% after confirmed implementation fixes.** Ordinary recruiting words such as `role` had falsely been interpreted as security roles, and sparse retrieval had missed the decisive recruiting page.
3. **Flow 10 (52%) is primarily an evidence-retrieval failure.** The decisive cart and checkout evidence is in steps 7–10, but many claims were verified only against steps 1–6.
4. **Flows 11 and 12 expose verifier reasoning errors.** Gemini inferred result pages from visible search controls, treated inline forms as dedicated review panels, accepted only one side of conjunctive requirements, and sometimes cited screenshot indices that were not attached.
5. **The benchmark is still provisional.** Every item in flows 06 and 09–13 is marked `needs_review`. These numbers should currently be called *agreement with provisional manual labels*, not final benchmark accuracy.

Using the new V4 results for flows 06 and 09, the weighted provisional agreement across flows 04–13 is **128/203 = 63.1%**. The old deterministic flow-09 result is excluded and replaced by the V4 result.

There is no evidence that a general Gemini outage caused the low scores:

- Flow 06 V4: 46 Gemini calls, zero fallbacks or failures.
- Flow 09 V4: 30 Gemini calls, zero fallbacks or failures.
- Flows 10–13: 126 Gemini calls in total, zero fallbacks or final failures.
- Flow 08: one malformed JSON response caused one fallback.
- Flow 13: one request stalled because no client timeout existed; the resumed run completed with zero fallbacks.
- The earlier low flow-04 run was affected by 503 errors and a 24-call cap, but the clean rerun removed those problems.

## Current Clean-Run Overview

| Flow | Agreement | Technical validity | Main interpretation |
|---|---:|---|---|
| 04 Under Armour | 15/21 = 71.4% | Valid Gemini run, no fallback | Remaining disagreements mix strictness and label review |
| 05 Resy | 14/20 = 70.0% | Valid Gemini V2 run | Reasonable baseline |
| 06 Six Flags Careers | 14/22 = 63.6% | Clean Gemini V4 run, zero fallback | Improved; remaining errors are mostly over-acceptance |
| 07 Discogs | 14/18 = 77.8% | Valid Gemini V2 run | Best current clean result |
| 08 Amtrak | 13/20 = 65.0% | One malformed-response fallback | Rerun recommended |
| 09 AMC Theatres | 10/20 = 50.0% | Clean Gemini V4 run, zero fallback | Old 30% deterministic run superseded |
| 10 Six Flags Purchase | 13/25 = 52.0% | Valid Gemini V3 run | Retrieval missed late cart screens |
| 11 Carnival | 12/20 = 60.0% | Valid Gemini V3 run | Overclaiming and invalid screenshot citations |
| 12 Book Depository | 11/18 = 61.1% | Valid Gemini V3 run | Hallucinated result state and over-strict caveats |
| 13 Yellow Pages | 12/19 = 63.2% | Valid Gemini V3 run | Mixed verifier strictness and contrastive-label uncertainty |

## High-Level Error Taxonomy

### A. Run/configuration errors

- Flow 09 was launched with `verifier=deterministic`, despite its filename containing `clean_api`.
- A filename is therefore not sufficient evidence that a run used Gemini. Always inspect:
  - `metadata.verifier`
  - `metadata.gemini_image_verifier.prompt_version`
  - `fallbacks`
  - `failures`

### B. Hidden-property false positives

The hidden-property detector previously matched:

- any occurrence of `role` as a security role;
- any occurrence of `availability` as uptime.

This directly damaged flow 06 and flow 08. The patterns were narrowed to security/access-role and high-availability contexts.

### C. Evidence retrieval misses

Flow 10 is the clearest case. The screenshots visibly contain:

- quantity change in steps 8–9;
- cart quantity and mixed line items in step 10;
- subtotal, fee, tax, and total in step 10;
- `Modify Cart` in step 10;
- marketing and purchase acknowledgements in step 10;
- high-contrast controls in steps 7–10.

Yet the verifier frequently received only steps 1–6. Increasing `top-k` did not solve this because the text reranker still preferred early screens. The verifier now:

- supplements sparse retrieval with chronologically distributed screenshots;
- forces late/final state coverage for cart, checkout, result, review, confirmation, and state-change claims.

### D. Unsupported downstream inference

Gemini sometimes treated a visible button as proof of the state after clicking it:

- Carnival `REQ-13`: inferred cruise results although no results page exists.
- Book Depository `REQ-09`: inferred filtered results although the flow ends on the advanced-search form.
- Book Depository contrastive requirements: inferred result correctness without a results view.

The prompt now explicitly forbids inferring a downstream result, submitted state, navigation outcome, or completed action without a later screenshot.

### E. Partial-clause satisfaction

Gemini sometimes marked a conjunction as supported when only one clause held:

- Carnival `CONTR-06` requires exact-day filtering **in addition to** broad duration bands. Only broad bands are visible.
- Review-panel requirements were treated as satisfied merely because editable inline inputs existed.

The prompt now requires every material conjunctive clause to be supported.

### F. Negative evidence and abstention

The difficult distinction is:

- `NOT_FULFILLED`: the relevant state is fully visible and the required UI is absent or contradicted;
- `ABSTAIN`: the state needed to judge the claim is not shown.

Examples:

- Carnival exact-day filtering: the opened duration selector shows only broad bands, so `NOT_FULFILLED` is justified.
- Book Depository inline filters on a results page: no results page is shown, so `ABSTAIN` is safer.

## Detailed Review of the Lowest Runs

## Flow 09 — AMC Theatres, V4 result 50.0%

### Technical finding

The original 30% result was not a Gemini failure because it was not a Gemini run. The replacement V4 run used:

- `verifier: gemini-image`
- `prompt_version: GEMINI_IMAGE_CLAIM_VERIFICATION_V4`
- 30 Gemini calls
- zero fallbacks
- zero failures

Agreement improved to **10/20 = 50.0%**.

### Gold-label candidates

Some manual labels appear stricter than the requirement wording:

- `REQ-05`: likely `FULFILLED`. The requirement asks for an optional account-association mechanism, and the checkbox is visible; it does not require showing the completed association.
- `REQ-10`: likely `FULFILLED`. The requirement asks the UI to provide alternative channels, not to verify that telephone/theatre channels work.
- `REQ-08`: remains debatable. One invalid-input rejection supports the rule but does not prove the universal `only` condition.

### Pipeline/model problems

- `REQ-09`: pipeline returned `ABSTAIN`, while `PARTIALLY_FULFILLED` is more informative because the lookup setup is visible but successful balance return is not.
- `CONTR-02`: Gemini inferred that one visible format error proves distinction from a separate unrecognized-card lookup failure. Gold `PARTIALLY_FULFILLED` is preferable.
- `CONTR-03`: Gemini claimed guest-mode support without a guest comparison and even reasoned inconsistently about the account requirement. Gold `ABSTAIN` is preferable.
- `CONTR-04`: universal `all paths/resources` completeness is not established. Gold partial/abstain is safer.
- `CONTR-05`: the final shown state lacks the requested result screen. The pipeline still confused entered credentials with a result confirmation. Gold `NOT_FULFILLED` is defensible.
- `CONTR-06`: Gemini treated visible error feedback as proof that the submit action clearly tracks submittability. The screenshots show the action itself remains visually similar, so gold `NOT_FULFILLED` is defensible.

## Flow 06 — Six Flags Careers, V4 result 63.6%

### Confirmed pipeline defects

Five disagreements were directly affected by the false `role → security` classification:

- `REQ-08`: visible role title metadata became `HIDDEN`.
- `REQ-09`: visible role responsibilities became `HIDDEN`.
- `REQ-11`: application workflow for a selected role became non-UI-verifiable.
- `REQ-14`: visible role context became `HIDDEN`.
- `CONTR-02`: visible handoff for the chosen role became `HIDDEN`.

The V4 rerun fixed these failures: `REQ-05`, `REQ-06`, `REQ-08`, `REQ-09`, `REQ-14`, and `REQ-16` now match their manual labels.

### Retrieval defects

- `REQ-05`: gold evidence is step 5, which visibly contains department/team cards. Gemini received the job-detail screen instead.
- `REQ-06`: step 5 visibly contains `NOW HIRING LIFEGUARDS`; the retrieved early screens missed it.
- `REQ-16`: step 5 visibly contains `MEGA HIRING EVENT`; Gemini incorrectly interpreted unrelated park events from step 1.

### Likely manual-label issues

`REQ-12` asks the system to **communicate** perks, benefits, or value propositions. The screenshots visibly do that. The current gold label is `PARTIALLY_FULFILLED` because the truth of the benefits is hidden, but truth/enforcement is not part of the requirement wording. Recommended review:

- current: `PARTIALLY_FULFILLED`
- likely correction: `FULFILLED`

`REQ-11` is also wording-sensitive. “Can be launched” may be satisfied by a visible opening-specific `Apply now` action, even though the subsequent application form is not shown. Recommended review:

- current: `PARTIALLY_FULFILLED`
- plausible correction: `FULFILLED`

`CONTR-02` similarly asks for a visible handoff, with a dedicated opening page as an example. The opening-specific page and `Apply now` affordance may justify `FULFILLED`; the current `PARTIALLY_FULFILLED` label assumes a later post-click outcome is required.

### Labels that appear defensible

- `CONTR-01 = PARTIALLY_FULFILLED`: park context reaches the job page, but a downstream application-start state is not shown.
- `CONTR-05 = NOT_FULFILLED`: relevant pre-application states are visible and no dedicated review summary appears.
- `CONTR-03 = PARTIALLY_FULFILLED`: only one of the many visible team areas is exercised, so `every` is not proven.
- `CONTR-04 = ABSTAIN`: an `Apply now` affordance does not prove the opening is truly still active.
- `CONTR-06 = NOT_FULFILLED`: static category cards are navigation entry points, not direct in-page filtering/refinement.

### Remaining model behavior

The V4 run over-accepted universal and negative claims:

- `every visible department/team area`
- `only when actively accepting applications`
- `does not rely only on static category entry points`

These are model/prompt issues rather than API failures.

## Flow 10 — Six Flags Purchase, 52%

This is mostly a retrieval problem rather than a bad benchmark.

### Strong gold labels missed because step 10 was absent

- `REQ-15 = FULFILLED`: step 10 visibly shows subtotal, processing fee, tax, and total.
- `REQ-12 = FULFILLED`: step 10 visibly shows the configured add-on with quantity 2.
- `REQ-13 = FULFILLED`: step 10 combines a one-day ticket and go-kart add-on.
- `REQ-16 = FULFILLED`: step 10 includes `Modify Cart` before checkout.
- `REQ-17 = PARTIALLY_FULFILLED`: step 10 separates optional marketing consent from purchase acknowledgement.
- `REQ-18 = FULFILLED`: high-contrast mode is visible during the purchase flow.

### Earlier state-change miss

- `REQ-09 = FULFILLED`: steps 8 and 9 visibly change quantity from 1 to 2 before adding to cart.

### Contrastive labels

- `CONTR-03 = PARTIALLY_FULFILLED`: visible policy explanation plus unverified enforcement is reasonable.
- `CONTR-04 = PARTIALLY_FULFILLED`: visible monetary breakdown but unverifiable universal completeness is reasonable.
- `CONTR-05 = NOT_FULFILLED`: the relevant pre-checkout screen is visible and lacks fulfillment-method review controls.

No obvious broad gold-label correction is recommended for flow 10.

## Flow 11 — Carnival, 60%

The manual benchmark appears stronger than the pipeline on most disagreements.

- `REQ-08 = FULFILLED`: duration bands are visible, but Gemini cited unattached steps 5 and 6. This is a verifier consistency bug.
- `REQ-13 = PARTIALLY_FULFILLED`: no result page is shown; pipeline hallucinated results.
- `REQ-14 = ABSTAIN`: genuine availability/searchability cannot be judged from option lists.
- `CONTR-01 = PARTIALLY_FULFILLED`: the flow does not demonstrate leaving and returning.
- `CONTR-03 = ABSTAIN`: result completeness cannot be judged.
- `CONTR-04 = ABSTAIN`: no anonymous-user comparison exists.
- `CONTR-05 = NOT_FULFILLED`: inline search controls are not a dedicated review panel.
- `CONTR-06 = NOT_FULFILLED`: the visible selector contains broad bands only, not exact-day filtering.

No clear manual-label correction is recommended here.

## Flow 12 — Book Depository, 61.1%

- `REQ-09 = PARTIALLY_FULFILLED`: no submitted filtered-results view is visible. Gold is more defensible than pipeline `FULFILLED`.
- `REQ-10 = FULFILLED`: global header controls remain present. Pipeline over-interpreted “order status” as requiring an actual order-status value rather than preserved access.
- `REQ-11 = FULFILLED`: visible language and currency controls satisfy the selectable-locale mechanism.
- `CONTR-01 = PARTIALLY_FULFILLED`: no return from a filtered-results view is shown.
- `CONTR-03/04 = ABSTAIN`: result correctness/completeness cannot be judged without results.
- `CONTR-06 = ABSTAIN`: intended label says `NOT_FULFILLED`, but the current manual gold is safer because the required results view is absent entirely.

The current manual labels appear preferable to both the pipeline and some stale intended labels.

## Changes Implemented During Analysis

The following fixes are implemented locally and covered by tests:

1. Narrow hidden-property patterns for `role` and `availability`.
2. Retry malformed Gemini JSON responses.
3. Add a bounded configurable Gemini request timeout.
4. Reject positive decisions that cite no attached screenshot.
5. Tell Gemini to preserve original screenshot step indices.
6. Supplement sparse retrieval with distributed flow coverage.
7. Force final-state coverage for cart/result/review/state-change claims.
8. Forbid downstream-result inference from controls alone.
9. Require all material conjunctive clauses.
10. Require both sides of comparative claims.
11. Avoid double-penalizing an explicitly accepted `SUPPORTED_WITH_CAVEAT` interpretation caveat.
12. Add flow, requirement, claim, prompt-version, and evidence-step context to future usage logs.

All relevant tests pass: **56 passed**.

## What Can Improve Agreement Today

Priority order:

1. **Completed: rerun flow 09 with Gemini V4.** Agreement is now 50.0%, with zero fallbacks.
2. **Completed: rerun flow 06 with Gemini V4.** Agreement improved from 50.0% to 63.6%.
3. **Rerun flow 10 with V4.** This tests final-screen augmentation; it has the largest number of recoverable retrieval misses.
4. **Rerun flows 11 and 12 with V4.** This tests stricter downstream, comparison, and conjunction reasoning.
5. **Review gold labels before publishing aggregate metrics.**
   - Highest-priority candidates: flow 06 `REQ-12 → FULFILLED`; flow 09 `REQ-05/REQ-10 → FULFILLED`.
   - Preserve current flow-11 and flow-12 contrastive labels unless screenshot review reveals new evidence.
6. **Report two numbers separately:**
   - all provisional items;
   - accepted/reviewed items only.

The likely immediate improvement is substantial, but it must be measured by reruns rather than estimated as a final number. Flow 10 alone has at least eight disagreements directly tied to omitted late screenshots.

## Recommended Supervisor Wording

> I completed clean multimodal verification runs for flows 04–13. The current weighted agreement with the provisional manual benchmark is 63.1%. The originally reported 30% result for flow 09 was caused by accidentally using the deterministic verifier; a clean Gemini V4 rerun reached 50.0% with zero fallbacks. Flow 06 improved from 50.0% to 63.6% after fixing false hidden-property detection and screenshot coverage. The remaining disagreements mainly concern evidence retrieval, model over-inference for universal or negative requirements, and manual labels whose strictness does not always match the exact requirement wording. All labels in the lowest-scoring flows are still marked `needs_review`, so these values should be presented as preliminary agreement rather than final benchmark accuracy. The next step is to rerun flows 10–12 with V4 and complete adjudication of the disputed manual labels.

## Result Files for Sharing

- `data/generated/ui_verification_runs/04_underarmour_clean_api.json`
- `data/generated/ui_verification_runs/05_resy_790ba0ec-4e7d-4df0-ac86-ea52b3a73532_clean_api.json`
- `data/generated/ui_verification_runs/06_sixflags_19b955ba-fdcd-4345-b33a-fc6a88b5a85d_clean_api_v4.json`
- `data/generated/ui_verification_runs/07_discogs_8251e820-4b8a-4221-b2d9-8158cada3dcf_clean_api.json`
- `data/generated/ui_verification_runs/08_amtrak_845fbfa9-1b98-4df4-b7c5-4c71ef3e5b1b_clean_api.json`
- `data/generated/ui_verification_runs/09_amctheatres_925a2307-b2b7-4189-bf25-e3f463c24e1c_clean_api_v4.json`
- `data/generated/ui_verification_runs/10_sixflags_ee1e95ab-4c5d-44c6-b302-783fd13a471e_clean_api_v3.json`
- `data/generated/ui_verification_runs/11_carnival_6cf8ca9c-672d-426e-ab6c-c865475edcd4_clean_api_v3.json`
- `data/generated/ui_verification_runs/12_bookdepository_c472a4fe-33a0-4b6f-8d42-adcc067ba4ed_clean_api_v3.json`
- `data/generated/ui_verification_runs/13_yellowpages_34c474ef-389c-421d-acbf-de5531437083_clean_api_v3.json`

For a supervisor package, include this report plus the clean run JSON files. Do not include API keys, `.env`, or the raw global usage log.
