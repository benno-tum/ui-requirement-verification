# UI-verifiability and bounding-box evaluation

This audit evaluates two separate components without additional hosted-model calls:

- the deterministic UI-verifiability classifier against independently reviewed requirement labels;
- deterministic OCR text-region localization, conditional on a human-selected claim–step pair.

It does **not** evaluate general visual GUI grounding or end-to-end region retrieval. Until the review is complete, the thesis should describe UI-verifiability as preliminary classifier-versus-single-annotator alignment and bounding boxes as prototype support.

## Fixed audit bundle

The committed audit is `ui_bbox_focused_20260717`, generated with seed `20260717`.

- 72 UI-verifiability items: all 6 current `NOT_UI_VERIFIABLE` cases, all 43 structural audit candidates, and 27 stratified controls. Overlap between mandatory groups is removed deterministically.
- 75 bounding-box instances: 15 each from Mind2Web flows 02, 03, 04, and 08, plus 15 PURE Split/Merge transfer cases.
- Public manifests contain the review prompt, exact screenshot path, and asset metadata only.
- Private reference files contain existing UI labels and OCR proposals. Do not give those files to a reviewer.

The manifests and baseline metrics are under `data/annotations/evaluation_audits/ui_bbox_focused_20260717/`. Regenerate them deterministically with:

```bash
PYTHONPATH=src python scripts/build_evaluation_audit.py --ensure-ocr-boxes
```

The flag upgrades legacy text-only OCR sidecars with offline Tesseract word/line coordinates before sampling. Omit it when those coordinate sidecars already exist. The committed bundle currently contains 59 proposals and 16 explicit null-proposal cases; nulls are retained so proposal coverage remains measurable.

The baseline classifier-versus-current-gold result over all 300 accepted items is stored in `baseline_classifier_metrics.json`. Accuracy alone is misleading because the classifier predicts the majority class for 284/300 items; report balanced accuracy, macro-F1, per-class metrics, and κ with it.

## Running a blinded review

Start the API and frontend as usual:

```bash
PYTHONPATH=src uvicorn ui_verifier.api.main:app --reload
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173/evaluation`. The newest completed inspection dataset is selected by default. The dataset **Complete Gemini run — flows 01–13 (processed input, high-resolution review)** exposes all grounded regions from `bbox_gemini_grounded_regions_topk4_01_13_20260719`; the older focused OCR audit remains selectable for comparison. When an original high-resolution screenshot is available, the gallery uses it and independently rescales the x and y coordinates from the verifier asset into the original asset's pixel space. The page separately displays the source-run completion time and inspection-package build time. Quick judgments are stored separately from production verification outputs and never overwrite current gold.

Rebuild the gallery dataset after replacing or rerunning the package with:

```bash
python scripts/build_pipeline_bbox_inspection.py
```

### High-resolution grounding pilot

The initial flows 01–13 run sent the processed screenshots to Gemini without additional resizing in application code. For example, flow 01 step 04 was sent at `353×1280`; the inspection gallery can instead show its `1298×4701` original after deterministic coordinate scaling.

A controlled flow-01 pilot added `--image-variant preferred-original` and sent the actual original images to Gemini. The target “Great Escape” region did not become correct: its returned box changed from normalized `[12,100,30,200]` on the processed input to `[100,170,130,380]` on the original, but the latter still falls well below the header. Therefore, flows 02–13 were not rerun. This is evidence that higher source resolution alone does not make free-form model coordinates reliable; the next localization experiment should snap semantic model decisions to OCR or Set-of-Mark region proposals.

### UI-verifiability

The reviewer sees only requirement text and its screenshot flow. The page does not expose the current label, classifier output, fulfillment label, provenance, or annotator. For each item, record:

1. `UI_VERIFIABLE`, `PARTIALLY_UI_VERIFIABLE`, or `NOT_UI_VERIFIABLE`;
2. a short rationale;
3. confidence and, optionally, ambiguity.

Agreement metrics are withheld in the web interface until all 72 labels are submitted. This prevents partial metrics from revealing whether early answers matched the hidden reference. Because this is a targeted audit sample, its agreement statistics are not prevalence estimates for the whole corpus.

### Bounding boxes

Phase 1 hides the OCR proposal. On the exact recorded screenshot, choose one applicability category and add zero or more reference rectangles:

- `SINGLE_REGION`: one rectangular region is sufficient;
- `MULTI_REGION`: multiple disjoint regions are needed;
- `WHOLE_SCREEN_OR_TRANSITION`: the evidence is a screen-wide state or transition;
- `NO_VISIBLE_REGION`: the claim is not visibly supported on this screenshot.

Draw by dragging on the image. Rectangles can be resized from the lower-right handle or deleted. Locking Phase 1 makes applicability, boxes, and the evidence note immutable and then reveals the stored OCR proposal. Phase 2 records relevance, sufficiency, and one or more error categories. Optional OCR alternatives are only available after the reference is locked.

All coordinates are stored in original-image pixels with image width, height, path, SHA-256 asset hash, and coordinate-space metadata. The API rejects degenerate and out-of-bounds rectangles.

Existing production boxes remain viewable separately: select a flow, open **Verification runs**, choose the Amtrak v2 or PURE run, then use **Inspect manual vs pipeline**.

## Reporting and adjudication

After the colleague finishes both audits, create a report and a separate adjudication queue:

```bash
PYTHONPATH=src python scripts/evaluate_evaluation_audit.py \
  --audit-id ui_bbox_focused_20260717 \
  --reviewer-id colleague
```

The report includes completion counts; UI raw/per-class agreement, confusion matrix, unweighted and ordinal-weighted Cohen's κ; and bounding-box validity, coverage, maximum IoU, IoU thresholds, center-hit, human judgments, and Mind2Web/PURE splits. The generated `*_ui_adjudication_queue.json` contains only disagreements and leaves `adjudicated_label` blank.

Fill every adjudication decision and preview the updated 300-item classifier metrics without changing gold:

```bash
PYTHONPATH=src python scripts/apply_ui_evaluability_adjudication.py \
  data/annotations/evaluation_audits/ui_bbox_focused_20260717/reports/colleague_ui_adjudication_queue.json
```

Inspect the generated metrics preview. Only after adjudication is approved, repeat with `--apply`. That explicit flag updates the relevant verification-gold records and records audit provenance; the original colleague response remains unchanged.

## Completion gate

The reference evaluation is complete only when:

- all 72 UI items have independent labels and their disagreements are adjudicated;
- all 75 bounding-box items have locked reference metadata and prediction-quality judgments;
- asset hashes and dimensions still match the reviewed screenshots;
- final metrics are regenerated after adjudication.

## Interim inspection finding and grounding redesign (2026-07-19)

The lightweight gallery inspection produced a strong early failure signal for the OCR-only localizer: 14 instances were judged, of which 13 were marked `INCORRECT` and one `UNCERTAIN`; none was marked valid. This targeted sequence is not an accuracy estimate, but it is sufficient to reject top-1 OCR lexical overlap as the primary localization method. Typical errors include selecting a page title or nearby keyword instead of the specific value, range, control, link group, or UI state that provides evidence for the claim. Review notes are stored in `bbox_inspection_judgments.json` and remain separate from pipeline outputs.

The current experimental pipeline uses direct semantic grounding:

1. Gemini receives the screenshots already attached for claim verification; there is no additional hosted-model call. The completed all-flow run used the processed verifier assets, while a later flow-01 pilot tested the original-resolution assets separately.
2. The response includes zero or more claim-specific `evidence_regions` with `[ymin, xmin, ymax, xmax]` coordinates normalized to 0–1000.
3. Regions are converted back to original-image pixels and retain source, dimensions, coordinate space, semantic role, and description.
4. Multiple regions are allowed for conjunctive or distributed evidence.
5. A missing Gemini region remains unlocalized instead of being replaced automatically with an unrelated OCR top match.
6. OCR remains an auxiliary text hint and can later generate candidates for a Set-of-Mark variant, but it no longer decides the region for Gemini-verified evidence.

This is related to Set-of-Mark prompting, but intentionally lighter: the first revision asks the already-invoked multimodal verifier to ground its own decision. If direct model coordinates remain inconsistent, the next controlled comparison should overlay numbered OCR/UI-region candidates and ask the model to select the necessary marks. The inspection UI also links to each original full-resolution screenshot so review is not limited by the scaled gallery preview.

### Proposed next grounding experiment: candidate marks with grid fallback

The proposal already defines evidence localization as a modular stage after screenshot retrieval and cites SeeClick as grounded UI-understanding work. A Set-of-Mark-inspired variant therefore refines the planned localization module without changing the research question or claiming a new end-to-end verifier. It should be called **candidate-mark grounding** rather than an exact reproduction of Set-of-Mark when its candidates come from OCR and UI-region detectors instead of the segmentation models used in the paper.

Recommended pipeline:

1. Generate candidate regions on the exact high-resolution asset used for review: OCR words/lines merged into text blocks, simple UI contours or connected components for controls/cards, and optional segmentation proposals for non-text visual evidence.
2. Prune the candidates using the claim, the verifier's evidence description, OCR text, and selected screenshot step. Candidate generation must retain high recall; a missing candidate cannot be recovered by mark selection.
3. Overlay stable mark IDs and thin rectangles without covering the underlying text. Ask Gemini to select the smallest set of IDs that supports or contradicts the claim. Permit multiple marks and explicit `WHOLE_SCREEN_OR_TRANSITION`, `NO_VISIBLE_REGION`, and `NONE_OF_THE_MARKS` outcomes.
4. Map selected IDs back to stored pixel coordinates deterministically. Do not let a second coordinate conversion or free-coordinate response move the selected region.
5. If no candidate covers the evidence, show a coarse labeled grid, let the model select one or more cells, crop those cells at high resolution, regenerate candidates, and repeat mark selection. The grid is therefore a coarse-to-fine recovery mechanism, not the final evidence box.

This design directly addresses the observed Great Escape failure: candidates should separately represent the park-location text and the logo, and the model must select which indicator matches the claim instead of estimating an approximate normalized rectangle. The proposal stage remains measurable through two separate quantities: **candidate coverage** (was an acceptable region proposed?) and **mark-selection accuracy** (did the model choose it?).

The evidence for trying this is promising but not conclusive. [Set-of-Mark](https://arxiv.org/abs/2310.11441) reports improved visual grounding from numbered semantic regions and finds that adding boxes to numeric marks helps phrase grounding; it also shows that proposal quality bounds the achievable result and that poor mark placement can confuse the model. The original experiments focus on GPT-4V, so applicability to Gemini must be established experimentally. [SeeClick](https://aclanthology.org/2024.acl-long.505/) motivates specialized GUI grounding, while the web-agent study [SeeAct](https://arxiv.org/abs/2401.01614) reports that Set-of-Mark was not its most effective web-grounding strategy and instead benefited from combining visual input with HTML-derived candidates. A trained GUI grounder such as [UGround](https://arxiv.org/abs/2410.05243) is a heavier alternative if candidate-mark grounding remains unreliable.

Before rerunning flows 01–13, compare direct coordinates, grid-only grounding, and candidate-mark grounding on the existing reviewed failures. Report candidate coverage, selected-region relevance and sufficiency, coordinate validity, boxes per claim, image/token cost, and separate text versus non-text cases. A full rerun is justified only if the pilot improves the human inspection results.

#### Flow-01 OCR-refinement pilot (2026-07-19)

Repeated direct Gemini coordinates for the Great Escape header varied across runs and landed on neighboring navigation content. A pipeline refinement now treats Gemini's region description as the semantic decision and snaps it only when at least two meaningful OCR words form a nearby phrase on the same high-resolution asset. Explicit spatial language such as “in the header” constrains candidate selection to the corresponding page area. For the inspected claim, Gemini's raw pixel box `[220.66, 470.10, 493.24, 611.13]` was refined from the OCR phrase “Great Escape” to `[199.40, 20.60, 440.60, 62.40]`, covering the selected-park indicator at the top of the 1298×4701 screenshot. Both raw and refined coordinates remain stored for audit. This fixes the motivating instance but does not establish benchmark-wide localization quality; non-text regions and incorrect semantic descriptions still require candidate-mark or other grounding methods.

#### Flow-02 local OmniParser/Florence pilot (2026-07-20)

The GameStop flow was selected as a no-cost candidate-grounding pilot because it contains only four screenshots while its reviewed direct-coordinate boxes were weak. The pilot remains screenshot-only: OmniParser detects UI regions from clean screenshots, Tesseract produces original-resolution text-line proposals, and OmniParser's locally executed Florence-2 caption model describes clean 128×128 context crops. Mark IDs and rectangles are never included in the caption model input; they exist only in the review frontend.

The local package contains 235 captioned OmniParser UI regions and the existing OCR proposals. With batch size four on a 16 GB MacBook Pro CPU, the optimized pass captioned the remaining 178 regions in 105.5 seconds and reported 1,432 MiB peak resident memory. The detector weight is 268 MB and the caption weight is approximately 1.1 GB. Both model revisions are pinned in the generated metadata, while the model weights remain an external Hugging Face dependency rather than repository content.

For each claim, a deterministic ranker combines the Florence caption, direct OCR text, OCR text contained by a UI region, TF-IDF-style lexical matching, a small UI-caption prior, and a penalty for excessively large regions. The inspection frontend initially displays only the five highest-ranked candidates and can still reveal all UI or OCR proposals for diagnosing candidate-recall failures. Changing the selected claim triggers a new claim-specific ranking; accepting a candidate remains an evaluation-only record and does not overwrite the production prediction.

This pilot does not yet establish localization accuracy. Florence outputs include useful functional descriptions such as “Search button,” “Radius … selected,” and “Set as Home Store,” but also noisy captions. The method should therefore be evaluated as a two-stage system: candidate recall at 1/3/5 and human validity of the selected region. If acceptable evidence is absent from the top five, the reviewer can distinguish ranking failure from proposal failure by revealing all candidates. A full-flow rerun is not justified until this targeted review shows improvement over direct Gemini coordinates.

#### Candidate-mark containment and sufficiency gate (2026-07-21)

The Flow-07 candidate-mark iterations reduced the raw number of regions substantially, from 262 in the uncapped experiment to 56–59 in the sparse variants. They also exposed two distinct failure modes. In V4, Gemini selected an OmniParser container that overlapped the relevant menu but omitted the claim-specific section; the raw detector coordinate, stored candidate, pipeline output, and displayed coordinate were identical, ruling out a coordinate-transform defect. In V5, an explicit containment instruction caused Gemini to select the accurately localized word “Contribute,” but that isolated heading did not by itself establish the claim that contribution actions were available. Geometric containment and evidential sufficiency must therefore be evaluated separately.

The prompt was revised to state domain-independent containment and sufficiency criteria and to remove examples derived from inspected flows. This reduces adaptive overfitting risk, but does not validate the method. Prompt versions, model configuration, candidate-generator versions, and the decision to revise the prompt after inspected failures must be reported chronologically. Results used to tune the prompt are development evidence, not an unbiased final test set.

The localization pass is post-hoc and conditional: it receives existing claim text, claim status, verifier observation, and selected screenshot steps, and it preserves the source run's requirement and claim labels. Consequently, agreement between a localization rerun and its source labels is true by construction and must not be reported as new Gemini 2.5 verification accuracy. A separate verification run against manual gold is required for label accuracy. The localization experiment instead measures candidate coverage, region relevance, region sufficiency, boxes per localized claim-step, coordinate validity, latency, and cost.

The full-flow gate remains closed until the generalized prompt is tested on a flow not used to formulate its examples and a small blinded review shows acceptable relevance and sufficiency. Only after freezing the prompt should flows 01–13 be generated for the final review; further prompt changes after inspecting those flows would require treating them as development data or reserving a new held-out test subset.

The generalized V6 prompt was tested on Flow 12 as a held-out gate. It produced 37 valid-coordinate boxes for 42 claims; all 30 non-missing claims retained at least one box and all 12 missing claims had none. The gate nevertheless failed on sufficiency. Inspected outputs included a multiple-criteria claim localized only to one field, a review-state claim localized only to its submission button, and a signed-in locale-context claim localized only to a sign-out indicator. The model selected no supplemental regions. Flow 12 is therefore reclassified as development data and the full-run gate remains closed.

V7 removes the earlier verifier's free-text observation from the localization prompt while retaining the requirement, claim, status, and already-selected screenshot step. It asks the model to derive the complete set of required visible facts from the requirement and claim and to map each returned region to those facts. This is intended to reduce confirmation of an incomplete verifier rationale and make sufficiency inspectable. The instruction remains generic and does not mention any benchmark website or previously observed UI. Flow 13 is reserved as the final pre-freeze gate; if V7 is modified after inspecting Flow 13, that flow must also be treated as development data and a new independent reference source is required for an unbiased final gate.

V7 was frozen after the Flow-13 gate and then executed across flows 01–13 without further localization-instruction changes. Long per-step responses initially omitted task records in several flows; the transport layer was repaired by retrying absent task IDs in fixed batches of at most five under the identical V7 prompt. This recovery changes batching only and must be reported because co-batched tasks can theoretically affect model output. The completed package contains 541 claims and 697 valid-coordinate regions (1.29 regions per claim), including 642 selected candidate regions and 55 supplemental regions. The 100 recorded Gemini 2.5 Flash calls cost an estimated $0.8831. Source requirement and claim labels are preserved exactly and are not new accuracy predictions.

Eight non-missing claims received an explicit `NO_VISIBLE_REGION` response rather than a fabricated box. These primarily concern absence-based contradictions, post-transition behavior, or claims whose stated evidence is outside the inspected screenshot. They should be reported as localization abstentions and reviewed as potential claim-step or source-label inconsistencies. The frontend audit `gemini25flash_omnimark_v7_factcoverage_bbox_allflows_01_13_20260721` contains the 697 returned regions. Human review of relevance and sufficiency is still required before reporting localization accuracy.
