# Evidence-First Verification Pipeline

This package is the first modular skeleton for verifying textual UI requirements against ordered screenshot flows.
It is intentionally conservative: no `FULFILLED` label is emitted without visible evidence.

## Pipeline

```mermaid
flowchart LR
  A[PipelineInput] --> B[ScreenUnderstanding]
  B --> C[ScreenRepresentation]
  A --> D[RequirementUnderstanding]
  D --> E[RequirementClaim]
  C --> F[EvidenceRetriever]
  E --> F
  F --> G[ClaimVerifier]
  E --> G
  G --> H[LabelAggregator]
  D --> H
  H --> I[PipelineOutput]
```

## Modules

- `schemas.py`: Pydantic v2 models for screenshots, screen representations, requirements, claims, evidence, claim results, requirement results, and pipeline input/output.
- `screen_understanding.py`: Loads image metadata, preserves `step_index`, reads optional OCR or summary sidecars, extracts already available text from Mind2Web `steps.json` HTML, and returns `ScreenRepresentation`.
- `requirement_understanding.py`: Heuristic UI evaluability classifier and claim decomposition wrapper. It reuses the existing `ui_verifier.requirements.claim_decomposition` code.
- `evidence_retrieval.py`: Strategy-based retrieval with lexical default, optional TF-IDF if `sklearn` is installed, optional local text embedding retrieval if `sentence-transformers` and a local model path are available, and optional text-only LLM reranking over extracted screen text.
- `claim_verification.py`: Rule-based placeholder verifier. It supports strong, weak, missing, and hidden evidence cases but does not invent contradictions.
- `gemini_image_claim_verifier.py`: Optional screenshot-grounded Gemini verifier for claim status decisions after retrieval selects candidate evidence steps.
- `label_aggregation.py`: Deterministic label gates enforcing the evidence-first policy.
- `pipeline.py`: Dependency-injected orchestration so Gemini, OCR, retrieval, and fine-tuned components can be swapped in later.

## CLI

```bash
python scripts/run_verification_pipeline.py \
  --flow-dir data/processed/flows/mind2web/<flow_id> \
  --requirements requirements.json \
  --out data/generated/verification_pipeline/<flow_id>.json \
  --retriever lexical \
  --top-k 3
```

`--retriever` supports `lexical`, `tfidf`, `embedding`, and `llm`. TF-IDF and embedding retrieval fall back safely when optional libraries or local models are unavailable. The LLM retriever is text-only: it ranks claims against extracted screen text, OCR, and summaries, then passes selected screenshots to the verifier.

Claim decomposition is rules-first with an LLM fallback enabled by default. The fallback is only used for requirements where heuristic decomposition looks weak:

```bash
python scripts/run_verification_pipeline.py \
  --flow-dir data/processed/flows/mind2web/<flow_id> \
  --requirements requirements.json \
  --out data/generated/verification_pipeline/<flow_id>.json \
  --claim-provider deepseek \
  --claim-model deepseek-chat
```

The fallback sends failed decomposition cases in one batch. To force fully deterministic/offline decomposition, pass `--no-llm-claim-fallback`.

Screenshot-grounded claim verification can be enabled with Gemini:

```bash
python scripts/run_verification_pipeline.py \
  --flow-dir data/processed/flows/mind2web/<flow_id> \
  --requirements requirements.json \
  --out data/generated/verification_pipeline/<flow_id>.json \
  --retriever llm \
  --top-k 4 \
  --claim-provider deepseek \
  --claim-model deepseek-chat \
  --retriever-provider deepseek \
  --retriever-model deepseek-chat \
  --verifier gemini-image \
  --verifier-model gemini-2.5-flash-lite \
  --max-verifier-images 4 \
  --max-gemini-api-calls 24
```

`--top-k` controls how many candidate evidence steps each claim can receive from retrieval. `--max-verifier-images` controls how many of those selected screenshots are attached per claim to the image verifier. They are related but not the same parameter.

## Input Example

```json
{
  "requirements": [
    {
      "requirement_id": "REQ-01",
      "text": "The system shall show a checkout summary including subtotal, tax, and total."
    }
  ]
}
```

The CLI also accepts a plain list of requirement objects or a list of strings.

## Output Example

```json
{
  "flow_id": "example_flow",
  "results": [
    {
      "requirement_id": "REQ-01",
      "requirement_text": "The system shall show a checkout summary including subtotal, tax, and total.",
      "ui_evaluability": "UI_VERIFIABLE",
      "final_label": "PARTIALLY_FULFILLED",
      "claims": [
        {
          "claim_id": "REQ-01-C1",
          "claim_text": "The system shows a checkout summary.",
          "status": "SUPPORTED",
          "evidence": [
            {
              "step_index": 3,
              "screenshot_path": "step_03.png",
              "visible_observation": "lexical matched score 0.667 on visible terms: checkout, summary.",
              "confidence": 0.667,
              "source": "lexical"
            }
          ],
          "uncertainty_reasons": [],
          "rationale": "Retrieved visible evidence is strong enough for this placeholder verifier."
        }
      ],
      "evidence": [],
      "uncertainty_reasons": ["FLOW_COVERAGE_GAP"],
      "rationale": "At least one important claim has visible support, but another important claim is missing, hidden, or ambiguous."
    }
  ]
}
```

## Label Rules

- `FULFILLED`: Only when the requirement is UI-verifiable or partially UI-verifiable, all central observable claims are supported or acceptably partially supported, at least one evidence item exists, no claim is contradicted, and no central hidden claim remains unresolved.
- `PARTIALLY_FULFILLED`: At least one important claim is supported or partially supported, while another important claim is missing, hidden, or ambiguous. There must be no central visible contradiction.
- `NOT_FULFILLED`: Only when a central observable claim is contradicted by visible evidence.
- `ABSTAIN`: Used for insufficient screenshots, no useful evidence, not UI-verifiable requirements, hidden properties, backend-only behavior, security, payment processing, email delivery, ranking correctness, long-term persistence, and real-world external effects.

Missing evidence alone is not `NOT_FULFILLED`. No evidence means no `FULFILLED`.

## Dependency Policy

No new dependencies were added for this skeleton. The implementation reuses:

- `pydantic` for structured schemas.
- `pillow` for image metadata.
- Existing argparse script conventions.
- Existing flow helpers and requirement claim decomposition.
- Existing Gemini wrapper when optional LLM claim fallback is explicitly enabled.

Optional TF-IDF and embedding retrievers use guarded imports only. They do not make downloads or network calls during normal execution or tests.

## Current Limitations

- OCR is sidecar-only unless a future component is injected.
- Lexical retrieval is a deterministic fallback, not a semantic verifier.
- The rule-based claim verifier does not detect contradictions.
- The LLM retriever is text-only and depends on extracted text quality; it does not inspect screenshot pixels.
- The Gemini image verifier currently sends original PNG bytes without downscaling in this production path.
- Image verification is claim-level and can fall back to the deterministic verifier when the API call cap is reached.
- Bounding boxes are supported in the schema but not localized yet.
- Screen summaries are placeholders unless sidecar or HTML text exists.

## Future Extensions

- Gemini-based requirement understanding.
- Gemini-based claim verification over screenshots and retrieved evidence.
- OCR integration with text and bounding boxes.
- Embedding reranker over candidate evidence steps.
- Bounding box localization for evidence regions.
- Fine-tuning a UI evaluability classifier.
- Fine-tuning an evidence-step reranker.
- Fine-tuning claim decomposition while preserving the evidence-first output contract.
