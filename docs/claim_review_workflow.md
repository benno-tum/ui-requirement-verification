# Claim Review Workflow

This workflow is for continuing the verification-gold review without losing existing claim evidence.

## Current Data Sources

- `data/annotations/verification_gold/<flow_id>/verification_gold.json`
  - Main review target.
  - Contains requirement text, final verification label, claim statuses, claim evidence steps, item-level evidence note, and rationale.
- `data/annotations/requirements_gold/<flow_id>/gold_requirements.json`
  - Gold requirement text and older manual labels.
  - Does not store claim-level evidence.
- `data/annotations/requirements_candidate/<flow_id>/candidate_requirements.json`
  - Candidate/contrastive data.
  - Several files contain reviewed claim/evidence data, especially `CONTR-*` and some candidate-derived `REQ-*`.
- `requirement_claims.txt` and `requirement_claim_evidence_suggestions.txt`
  - Legacy exported claim/evidence review data.
  - These files are tracked but currently deleted in the worktree. They can be read from Git with `git show HEAD:<file>`.

Do not regenerate or backfill `verification_gold` from scratch unless you first make a backup and know which source you want to preserve.

## Before Reviewing

Run the backend and frontend:

```bash
PYTHONPATH=src uvicorn ui_verifier.api.main:app --reload
cd frontend
npm run dev
```

Open the frontend and use the Verification Gold editor, not only the candidate editor.

Before a review session, check the current state:

```bash
git status --short
PYTHONPATH=src:. python - <<'PY'
import json
from pathlib import Path

for path in sorted(Path("data/annotations/verification_gold").glob("*/verification_gold.json")):
    data = json.loads(path.read_text())
    items = data.get("items", [])
    claims = [claim for item in items for claim in item.get("claims", [])]
    accepted = sum(1 for item in items if item.get("review_status") == "accepted")
    missing_note = sum(1 for claim in claims if not claim.get("note"))
    print(data["flow_id"], "items", len(items), "claims", len(claims), "accepted", accepted, "claims_without_note", missing_note)
PY
```

## What To Review Per Requirement

For each `needs_review` item:

1. Confirm the requirement text is still the intended benchmark item.
2. Confirm `ui_evaluability`:
   - `UI_VERIFIABLE`: visible UI evidence is enough.
   - `PARTIALLY_UI_VERIFIABLE`: visible UI core exists, but hidden state/persistence/external behavior also matters.
   - `NOT_UI_VERIFIABLE`: screenshots cannot judge it.
3. Confirm `verification_label`:
   - `FULFILLED`: all observable core claims are supported.
   - `PARTIALLY_FULFILLED`: some important claim is supported, but some important part is missing/hidden/ambiguous.
   - `NOT_FULFILLED`: visible counter-evidence exists.
   - `ABSTAIN`: no reliable positive or negative judgment.
4. Review every claim:
   - Claim text is atomic and derived from the requirement, not from screenshot details.
   - `status` is one of `SUPPORTED`, `CONTRADICTED`, `MISSING`, `HIDDEN`, `AMBIGUOUS`, `OUT_OF_SCOPE`.
   - `claim_type` is `OBSERVABLE` or `HIDDEN`.
   - `importance` is `CORE` or `SUPPORTING`.
   - `evidence_steps` are set for supported/contradicted observable claims.
   - `note` briefly explains the evidence or why it is missing/hidden/ambiguous.
5. Confirm item-level `evidence_steps`, `evidence_note`, and `rationale`.
6. Only set `review_status` to `accepted` when the item is internally consistent.

## Claim Status Rules

- Use `SUPPORTED` only when the screenshot flow visibly supports the claim.
- Use `CONTRADICTED` only with visible counter-evidence.
- Use `MISSING` when the claim could be visible, but the flow does not show enough.
- Use `HIDDEN` for persistence, backend state, email delivery, payment processing, account storage, security, ranking correctness, or later visits.
- Use `AMBIGUOUS` when there is visible evidence but the interpretation is unstable.
- Use `OUT_OF_SCOPE` for routine internal effects that are not the screenshot verification target.

Missing evidence alone is not `NOT_FULFILLED`.

## Suggested Review Order

Use `docs/systematic_error_analysis_and_review_plan_2026-07-02.md` as the current review map.

1. Review `needs_review` items with label mismatches first.
2. Start with over-fulfilled cases where the prediction is `FULFILLED` but gold is weaker or abstains.
3. Then review gold-`ABSTAIN` cases where the model predicts a concrete label.
4. Then review under-called cases with no evidence overlap, especially late cart, checkout, result, review, and summary states.
5. After label mismatches, review label-correct cases whose evidence has no overlap with gold evidence.
6. For each flow, review `REQ-*` before `CONTR-*`.
7. For `CONTR-*`, pay special attention to hidden, persistence, completeness, validity, availability, and long-term requirements.
8. After each flow, run validation and commit or at least save a backup.

Recommended flow order for the current benchmark:

1. Flow 10: strongest late-state/top-k issue.
2. Flow 09: many over-fulfillment and abstain-boundary issues.
3. Flow 06: strong universal/comparative over-fulfillment pattern.
4. Flows 11, 12, and 13: result/search/persistence and hidden-property boundaries.
5. Flows 04, 05, 07, and 08: smaller cleanup.
6. Flows 01-03: lower manual-review priority, but flow 01 remains technically flagged because older runs had API fallback issues.

Use one short review tag in `annotation_notes` or the review notes while adjudicating:

- `model_over_fulfilled`
- `model_should_abstain`
- `retrieval_missed_late_state`
- `label_boundary`
- `gold_label_update_candidate`

## Model-Assisted Review Bundles

The generated bundles are under:

```text
data/generated/claim_review_bundles/
```

Each flow has a ZIP with:

- `prompt.md`
- `claim_review_input.json`
- `task.json`
- `images/step_XX.png`

Use these bundles to ask a model for claim-level review suggestions. Treat model output as suggestions only. The human-reviewed source of truth remains `verification_gold`.

After importing or manually applying model suggestions, verify:

```bash
PYTHONPATH=src:. python - <<'PY'
from pathlib import Path
from ui_verifier.verification.schemas import VerificationGoldFile

for path in sorted(Path("data/annotations/verification_gold").glob("*/verification_gold.json")):
    VerificationGoldFile.load(path)
print("verification_gold files load successfully")
PY
```

## Avoiding Data Loss

Before running any script that writes `verification_gold`, make a backup:

```bash
ts=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "data/generated/manual_backups/$ts"
cp -R data/annotations/verification_gold "data/generated/manual_backups/$ts/"
```

Avoid these unless you explicitly intend to overwrite review data:

```bash
python scripts/backfill_verification_claim_suggestions.py --replace-existing
python scripts/backfill_verification_claim_suggestions.py --replace-trivial-copied
```

If richer claim data appears missing again, check:

```bash
git show HEAD:requirement_claim_evidence_suggestions.txt
data/annotations/requirements_candidate/<flow_id>/candidate_requirements.json
data/generated/verification_gold_recovery_backups/
data/generated/evidence_import_backups/
```

Recovery script:

```bash
PYTHONPATH=src:. python scripts/recover_legacy_claim_evidence.py --dry-run
PYTHONPATH=src:. python scripts/recover_legacy_claim_evidence.py
```

Run recovery only after inspecting the dry run.
