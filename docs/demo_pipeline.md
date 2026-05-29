# Demo Verification Pipeline

This demo runs the evidence-first verifier on real local Mind2Web flows from the repository dataset.
It uses existing gold requirements, ordered `step_*.png` screenshots, optional OCR sidecars, claim-level evidence retrieval, and deterministic requirement labeling.

## Default Demo

Run from the repository root:

```bash
PYTHONPATH=src:. python scripts/run_demo_verification.py --flow-id 03_mbta
```

The command resolves `03_mbta` to the full local flow id, prefers screenshots under:

```text
data/processed/flows/mind2web/<flow_id>/step_*.png
```

and falls back to:

```text
data/generated/candidate_requirements/<flow_id>/manual_harvest_bundle/images/step_*.png
```

The default output is:

```text
data/generated/demo_verification/<flow_id>.json
data/generated/demo_verification/<flow_id>.md
data/generated/demo_verification/<flow_id>_artifacts/
```

The artifact directory contains stage-by-stage files for slides or a later handout:

```text
00_run_summary.json
01_screenshot_flow.json
02_ocr_summary.json
03_screen_representations.json
04_claims.json
05_evidence_by_requirement.json
06_reference_comparison.json
pipeline_trace.md
```

The Markdown report includes requirement-level predicted labels, reviewed-label comparison against `verification_gold`, claim statuses, evidence steps, and evidence snippets.

## Frontend

The frontend can show the latest generated demo run in a read-only tab.

1. Generate a run:

   ```bash
   PYTHONPATH=src:. python scripts/run_demo_verification.py --flow-id 03_mbta
   ```

2. Start the backend:

   ```bash
   PYTHONPATH=src:. uvicorn ui_verifier.api.main:app --reload
   ```

3. Start the frontend:

   ```bash
   cd frontend
   npm run dev
   ```

4. Open the flow and select the `Demo run` tab.

The tab reads `GET /flows/<flow_id>/demo-verification/latest` and is separate from the editable verification-gold review UI.

## OCR

By default, the demo generates missing OCR sidecars with local Tesseract when available:

```text
data/processed/flows/mind2web/<flow_id>/ocr/step_03.json
```

These sidecars are already consumed by `ScreenUnderstanding`.
If Tesseract is unavailable, the demo continues with HTML metadata or existing sidecars and records the limitation in output metadata.

Useful variants:

```bash
PYTHONPATH=src:. python scripts/run_demo_verification.py --flow-id 03_mbta --ocr never
PYTHONPATH=src:. python scripts/run_demo_verification.py --flow-id 03_mbta --ocr force
```

OCR can also be run directly:

```bash
PYTHONPATH=src:. python scripts/generate_ocr_sidecars.py \
  --flow-dir data/processed/flows/mind2web/03_mbta_c094948f-afc6-415c-968a-9e105e2db118
```

## Claims

Claims are kept for the demo, but used lightly.
They explain why a requirement is partially fulfilled, missing evidence, hidden, or abstained.
Atomic requirements fall back to exactly one claim, so the demo does not depend on perfect decomposition.

## Gemini / MLLM

The demo path is deterministic by default and does not require an API key.
The current command does not use a Gemini vision verifier; output metadata records `gemini_mllm_verifier_used: false`.
The optional existing text-only claim-decomposition fallback can be requested with:

```bash
PYTHONPATH=src:. python scripts/run_demo_verification.py --flow-id 03_mbta --llm-claim-fallback
```

If `GEMINI_API_KEY` is missing, the script falls back to deterministic claim decomposition.

## Image-Based Gemini Verification

The demo also has an optional image-primary verifier:

```bash
PYTHONPATH=src:. python scripts/run_demo_verification.py \
  --flow-id 08_amtrak \
  --verifier gemini-image \
  --screen-source image-only
```

In `image-only` mode:

- raw HTML is removed from screen metadata before screen understanding
- non-image sidecar text is not passed to the final Gemini verifier
- Tesseract OCR may be used only as an image-derived hint
- screenshots are always attached to the Gemini claim-verification request

Gemini claim outputs are cached under:

```text
data/generated/demo_verification/<flow_id>_artifacts/gemini_image_claim_verification.json
```

If Gemini fails, `GEMINI_API_KEY` is missing, or the returned JSON is invalid, the affected claim falls back to deterministic verification.
The demo caps uncached Gemini image calls at 10 per run by default so meeting demos return predictably under free-tier rate limits.
Use `--max-gemini-api-calls -1` to remove the cap, or rerun the same command to fill the cache incrementally.
Use `--gemini-max-retries N` if you deliberately want the command to wait and retry quota/high-demand responses.
Output metadata reports:

- `screen_source_mode`
- `raw_html_used`
- `ocr_used`
- `screenshot_images_used`
- `gemini_mllm_verifier_used`
- `gemini_image_verifier`

## Label Rules

- `FULFILLED` requires visible evidence for all central observable claims.
- `PARTIALLY_FULFILLED` is used when some important observable evidence is present but other important parts are missing, hidden, or ambiguous.
- `NOT_FULFILLED` requires visible contradiction.
- `ABSTAIN` is used for insufficient evidence or non-UI-verifiable requirements.
- Missing evidence alone is never treated as `NOT_FULFILLED`.

## Flow Choice For Presentation

`03_mbta` is a good walkthrough flow because it has 14 ordered screenshots and shows a realistic multi-step careers workflow.
The deterministic demo currently matches 12 of 16 comparable reviewed labels for `03_mbta`, with mismatches mostly caused by over-predicting `FULFILLED` where the reviewed reference is `PARTIALLY_FULFILLED`.

`08_amtrak` is a cleaner fallback if the presentation goal is agreement with reviewed labels.
It has only 5 screenshots, and the deterministic demo currently matches 11 of 12 comparable reviewed labels.

Use `03_mbta` to explain the pipeline and limitations; use `08_amtrak` if you want a smoother label-compliance demo.

## Deliberately Left Out

- Full bounding-box localization
- Research-grade visual grounding
- Robust contradiction detection
- Full transition-level ordered-flow reasoning
- PURE integration
- Fine-tuning and large-scale evaluation
