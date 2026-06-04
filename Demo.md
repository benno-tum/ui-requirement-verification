# Demo Tomorrow

This note is for the meeting demo of the image-based verification path. The current
`gemini-image` verifier path is stable enough for the meeting and should be treated
as the demo path, not as a final production verifier.

## Start Backend

From the repository root:

```bash
PYTHONPATH=src:. uvicorn ui_verifier.api.app:app --reload --host 127.0.0.1 --port 8000
```

## Start Frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

Open the Vite URL printed by the frontend, usually:

```text
http://localhost:5173
```

## Run Demo Verification

Recommended stable demo flow:

```bash
PYTHONPATH=src:. python scripts/run_demo_verification.py --flow-id 08_amtrak --verifier gemini-image --screen-source image-only --no-clipboard
```

The latest generated artifacts are written to:

```text
data/generated/demo_verification/08_amtrak_845fbfa9-1b98-4df4-b7c5-4c71ef3e5b1b.json
data/generated/demo_verification/08_amtrak_845fbfa9-1b98-4df4-b7c5-4c71ef3e5b1b.md
data/generated/demo_verification/08_amtrak_845fbfa9-1b98-4df4-b7c5-4c71ef3e5b1b_artifacts/
```

The frontend can show the latest generated result in the demo verification view for
the selected flow.

## How To Explain Image-Only Mode

`--screen-source image-only` means the final Gemini verifier treats screenshots as
the primary semantic evidence. Raw HTML and non-image sidecar text are excluded from
the final verifier. The verifier may still receive bookkeeping metadata such as step
index, screenshot path, width, and height, but these are not semantic evidence.

The intended meeting framing:

- The system verifies reviewed textual UI requirements against ordered screenshot
  flows.
- Each requirement is decomposed into lightweight claims.
- Evidence is retrieved from the screenshot sequence.
- Gemini verifies claims from selected screenshot images.
- The final requirement label is aggregated from claim-level verification.

## OCR In This Demo

OCR is allowed only as an image-derived auxiliary hint. In the current demo it comes
from local Tesseract sidecars generated from the screenshots. OCR can help retrieval
and can be passed as a clearly marked hint, but screenshots remain the primary
evidence for Gemini in `image-only` mode.

For the stable `08_amtrak` run, the expected metadata is:

```text
screen_source_mode=image-only
raw_html_used=False
ocr_used=True
screenshot_images_used=True
gemini_mllm_verifier_used=True
```

## Cache And Fallback

Gemini image verification is cached under the artifacts directory:

```text
data/generated/demo_verification/<flow_id>_artifacts/gemini_image_claim_verification.json
```

For the warmed `08_amtrak` demo, the cache should avoid new API calls and prevent
quota surprises. The expected stable behavior is high cache hits and zero fallbacks.

If Gemini is unavailable, returns invalid JSON, or quota is exhausted, the pipeline
falls back to the deterministic verifier and records that in metadata. This keeps
the demo runnable, but fallback results should be explained as a robustness path,
not as the desired MLLM verification mode.

## Known Limitation

Gemini free-tier quota can trigger fallback on larger or uncached flows. The
`03_mbta` flow is useful for showing richer evidence and limitations, but it has
previously hit free-tier Gemini request limits during uncached image verification.

This demo should be presented as a working image-based MLLM verification path, not
as a fully production-ready cost-controlled verifier yet.

## Next Steps After The Meeting

- Set up paid Gemini 2.5 Flash access or university API credits for repeated
  evaluation runs.
- Add usage logging and cost governance.
- Run larger evaluations across more reviewed flows.
- Consider local models such as Qwen-VL as future work.
- Consider fine-tuning only as later research work, after the evaluation protocol is
  stable.
