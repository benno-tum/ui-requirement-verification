from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ui_verifier.annotation.service import AnnotationService
from ui_verifier.api.flow_catalog import FlowCatalog
from ui_verifier.requirement_inspection.schemas import UiEvaluability
from ui_verifier.requirements.candidate_generation import generate_harvested_for_flow
from ui_verifier.requirements.gemini_client import run_gemini
from ui_verifier.requirements.schemas import RequirementReviewStatus
from ui_verifier.common.json_utils import parse_json_response
from ui_verifier.verification.schemas import UIEvaluability, VerificationLabel
from ui_verifier.verification.service import VerificationService
from ui_verifier.verification.storage import VerificationStorage


def _ensure_static_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


app = FastAPI(title="UI Verifier API")
annotation_service = AnnotationService()
verification_service = VerificationService(annotation_service=annotation_service)
verification_storage = VerificationStorage()
flow_catalog = FlowCatalog(annotation_storage=annotation_service.storage, verification_storage=verification_storage)
DEMO_VERIFICATION_ROOT = Path(__file__).resolve().parents[3] / "data" / "generated" / "demo_verification"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/flows", StaticFiles(directory=str(_ensure_static_dir(flow_catalog.flows_root))), name="flow_static")
app.mount(
    "/static/candidate_artifacts",
    StaticFiles(directory=str(_ensure_static_dir(annotation_service.storage.candidate_root))),
    name="candidate_artifact_static",
)


class AcceptCandidateRequest(BaseModel):
    edited_text: str | None = None
    edited_step_indices: list[int] | None = None
    edited_tags: list[str] | None = None
    annotation_notes: str | None = None
    annotated_by: str | None = None
    review_status: str | None = None
    verification_label: str | None = None
    ui_evaluability: str | None = None
    uncertainty_reasons: list[str] | None = None
    claims: list[dict[str, Any]] | None = None
    evidence_steps: list[int] | None = None
    evidence_note: str | None = None
    rationale: str | None = None
    manual_verification_label: str | None = None
    manual_verification_notes: str | None = None


class RejectCandidateRequest(BaseModel):
    reason: str | None = None
    annotated_by: str | None = None


class UpdateCandidateRequest(BaseModel):
    edited_text: str | None = None
    edited_step_indices: list[int] | None = None
    edited_tags: list[str] | None = None
    annotation_notes: str | None = None
    annotated_by: str | None = None
    review_status: str | None = None
    verification_label: str | None = None
    ui_evaluability: str | None = None
    uncertainty_reasons: list[str] | None = None
    claims: list[dict[str, Any]] | None = None
    evidence_steps: list[int] | None = None
    evidence_note: str | None = None
    rationale: str | None = None
    benchmark_decision: str | None = None
    ui_evaluability: str | None = None
    visible_subtype: str | None = None
    requirement_type: str | None = None


class UpdateGoldRequirementRequest(BaseModel):
    edited_text: str | None = None
    edited_step_indices: list[int] | None = None
    edited_tags: list[str] | None = None
    annotation_notes: str | None = None
    annotated_by: str | None = None
    manual_verification_label: str | None = None
    manual_verification_notes: str | None = None


class UpdateVerificationGoldRequest(BaseModel):
    edited_text: str | None = None
    edited_step_indices: list[int] | None = None
    edited_tags: list[str] | None = None
    annotation_notes: str | None = None
    annotated_by: str | None = None
    review_status: str | None = None
    verification_label: str | None = None
    ui_evaluability: str | None = None
    uncertainty_reasons: list[str] | None = None
    claims: list[dict[str, Any]] | None = None
    evidence_steps: list[int] | None = None
    evidence_note: str | None = None
    rationale: str | None = None


class VerifyFlowRequest(BaseModel):
    flow_dir: str
    steps: str | None = None
    max_images: int | None = 4
    image_max_side: int = 1024
    model_name: str = "gemini-2.5-flash"
    dry_run: bool = True


class GenerateHarvestedRequest(BaseModel):
    max_images: int | None = 6
    image_max_side: int = 1280
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.7
    hybrid_mode: bool = False
    pure_prior_top_k: int = 6


class RebuildCandidatesRequest(BaseModel):
    candidate_model_name: str = "gemini-2.5-flash-lite"
    allow_overwrite_with_gold: bool = False


class RephraseClaimRequest(BaseModel):
    requirement_text: str
    claim_text: str
    feedback: str
    claim_status: str | None = None
    claim_type: str | None = None
    importance: str | None = None
    model_name: str = "gemini-2.5-flash-lite"
    temperature: float = 0.1


def _build_claim_rephrase_prompt(body: RephraseClaimRequest) -> str:
    return f"""Rewrite one UI verification claim.

Requirement:
{body.requirement_text.strip()}

Current bad claim:
{body.claim_text.strip()}

Reviewer feedback about what is wrong or what the new claim should include:
{body.feedback.strip()}

Current claim metadata:
status: {body.claim_status or "not set"}
claim_type: {body.claim_type or "not set"}
importance: {body.importance or "not set"}

Rules:
- Return a replacement claim only.
- The claim must be an atomic English sentence.
- Keep it checkable from ordered UI screenshots when possible.
- Do not add rationale, notes, evidence, labels, or markdown.
- Do not mention that this is a rewrite.
- Do not preserve wording the reviewer explicitly said is wrong.

Return JSON only:
{{"claim_text": "<replacement claim>"}}"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/flows")
def list_flows() -> list[dict[str, Any]]:
    return flow_catalog.list_flows()


@app.get("/flows/{flow_id}")
def get_flow(flow_id: str) -> dict[str, Any]:
    try:
        return flow_catalog.get_flow(flow_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/flows/{flow_id}/steps")
def get_flow_steps(flow_id: str) -> list[dict[str, Any]]:
    try:
        return flow_catalog.get_flow_steps(flow_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e




@app.get("/flows/{flow_id}/harvested")
def list_harvested_requirements(flow_id: str) -> list[dict[str, Any]]:
    try:
        reqs = annotation_service.list_harvested(flow_id)
        return [r.to_dict() for r in reqs]
    except FileNotFoundError:
        return []




@app.post("/flows/{flow_id}/harvested/generate")
def generate_harvested_requirements(
    flow_id: str,
    body: GenerateHarvestedRequest,
) -> dict[str, Any]:
    try:
        _, flow_dir = flow_catalog.resolve_flow(flow_id)
        harvest_file = generate_harvested_for_flow(
            flow_dir=flow_dir,
            output_root=annotation_service.storage.candidate_root,
            steps_arg=None,
            max_images=body.max_images,
            image_max_side=body.image_max_side,
            dry_run=False,
            model_name=body.model_name,
            temperature=body.temperature,
            hybrid_mode=body.hybrid_mode,
            pure_prior_top_k=body.pure_prior_top_k,
        )
        if harvest_file is None:
            raise ValueError("Harvest generation did not produce any requirements")
        return {
            "flow_id": flow_id,
            "harvested_count": len(harvest_file.requirements),
            "requirements": [r.to_dict() for r in harvest_file.requirements],
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/flows/{flow_id}/candidates/rebuild-from-harvested")
def rebuild_candidates_from_harvested(
    flow_id: str,
    body: RebuildCandidatesRequest,
) -> dict[str, Any]:
    try:
        candidate_file = annotation_service.rebuild_candidates_from_harvested(
            flow_id,
            candidate_model_name=body.candidate_model_name,
            allow_overwrite_with_gold=body.allow_overwrite_with_gold,
        )
        return {
            "flow_id": flow_id,
            "candidate_count": len(candidate_file.requirements),
            "requirements": [r.to_dict() for r in candidate_file.requirements],
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/flows/{flow_id}/candidates")
def list_candidates(flow_id: str, only_pending: bool = False) -> list[dict[str, Any]]:
    try:
        reqs = annotation_service.list_candidates(flow_id, only_pending=only_pending)
        return [r.to_dict() for r in reqs]
    except FileNotFoundError:
        return []


@app.get("/flows/{flow_id}/gold")
def list_gold_requirements(flow_id: str) -> list[dict[str, Any]]:
    try:
        reqs = annotation_service.list_gold_requirements(flow_id)
        return [r.to_dict() for r in reqs]
    except FileNotFoundError:
        return []


@app.get("/flows/{flow_id}/verification-gold")
def list_verification_gold(flow_id: str) -> list[dict[str, Any]]:
    try:
        items = annotation_service.list_verification_gold(flow_id)
        return [item.to_dict() for item in items]
    except FileNotFoundError:
        return []


@app.get("/flows/{flow_id}/verification/latest")
def get_latest_verification_run(flow_id: str) -> dict[str, Any]:
    try:
        return verification_storage.load_run(flow_id).to_dict()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/flows/{flow_id}/demo-verification/latest")
def get_latest_demo_verification_run(flow_id: str) -> dict[str, Any]:
    path = DEMO_VERIFICATION_ROOT / f"{flow_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Demo verification run not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid demo verification JSON: {path}") from e
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=f"Demo verification JSON must be an object: {path}")
    return data


@app.post("/flows/{flow_id}/candidates/{requirement_id}/accept")
def accept_candidate(
    flow_id: str,
    requirement_id: str,
    body: AcceptCandidateRequest,
) -> dict[str, Any]:
    try:
        req = annotation_service.accept_candidate(
            flow_id,
            requirement_id,
            edited_text=body.edited_text,
            edited_step_indices=body.edited_step_indices,
            edited_tags=body.edited_tags,
            annotation_notes=body.annotation_notes,
            annotated_by=body.annotated_by,
            review_status=body.review_status,
            verification_label=VerificationLabel(body.verification_label) if body.verification_label else None,
            ui_evaluability=UiEvaluability(body.ui_evaluability) if body.ui_evaluability else None,
            uncertainty_reasons=body.uncertainty_reasons,
            claims=body.claims,
            evidence_steps=body.evidence_steps,
            evidence_note=body.evidence_note,
            rationale=body.rationale,
            manual_verification_label=body.manual_verification_label,
            manual_verification_notes=body.manual_verification_notes,
        )
        return req.to_dict()
    except (FileNotFoundError, KeyError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/flows/{flow_id}/candidates/{requirement_id}/review")
def review_candidate(
    flow_id: str,
    requirement_id: str,
    body: UpdateCandidateRequest,
) -> dict[str, Any]:
    try:
        req = annotation_service.update_candidate(
            flow_id,
            requirement_id,
            edited_text=body.edited_text,
            edited_step_indices=body.evidence_steps if body.evidence_steps is not None else body.edited_step_indices,
            edited_tags=body.edited_tags,
            annotation_notes=body.annotation_notes,
            annotated_by=body.annotated_by,
            review_status=RequirementReviewStatus(body.review_status) if body.review_status else None,
            ui_evaluability=UiEvaluability(body.ui_evaluability) if body.ui_evaluability else None,
            verification_label=body.verification_label,
            uncertainty_reasons=body.uncertainty_reasons,
            claims=body.claims,
            evidence_steps=body.evidence_steps,
            evidence_note=body.evidence_note,
            rationale=body.rationale,
        )
        req = annotation_service.mark_needs_review(flow_id, requirement_id)
        return req.to_dict()
    except (FileNotFoundError, KeyError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/flows/{flow_id}/candidates/{requirement_id}/reject")
def reject_candidate(
    flow_id: str,
    requirement_id: str,
    body: RejectCandidateRequest,
) -> dict[str, Any]:
    try:
        req = annotation_service.reject_candidate(flow_id, requirement_id)
        return {
            "requirement_id": req.requirement_id,
            "flow_id": req.flow_id,
            "review_status": req.review_status.value,
            "reason": body.reason,
            "annotated_by": body.annotated_by,
        }
    except (FileNotFoundError, KeyError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/flows/{flow_id}/candidates/{requirement_id}/needs-review")
def mark_candidate_needs_review(flow_id: str, requirement_id: str) -> dict[str, Any]:
    try:
        req = annotation_service.mark_needs_review(flow_id, requirement_id)
        return req.to_dict()
    except (FileNotFoundError, KeyError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/flows/{flow_id}/gold/{requirement_id}")
def update_gold_requirement(
    flow_id: str,
    requirement_id: str,
    body: UpdateGoldRequirementRequest,
) -> dict[str, Any]:
    try:
        req = annotation_service.update_gold_requirement(
            flow_id,
            requirement_id,
            edited_text=body.edited_text,
            edited_step_indices=body.edited_step_indices,
            edited_tags=body.edited_tags,
            annotation_notes=body.annotation_notes,
            annotated_by=body.annotated_by,
            manual_verification_label=body.manual_verification_label,
            manual_verification_notes=body.manual_verification_notes,
        )
        return req.to_dict()
    except (FileNotFoundError, KeyError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/flows/{flow_id}/verification-gold/{requirement_id}")
def update_verification_gold_item(
    flow_id: str,
    requirement_id: str,
    body: UpdateVerificationGoldRequest,
) -> dict[str, Any]:
    try:
        verification_label = (
            VerificationLabel(body.verification_label.strip().upper()) if body.verification_label else None
        )
        ui_evaluability = (
            UIEvaluability(body.ui_evaluability.strip().upper()) if body.ui_evaluability else None
        )
        item = annotation_service.update_verification_gold_item(
            flow_id,
            requirement_id,
            edited_text=body.edited_text,
            edited_step_indices=body.edited_step_indices,
            edited_tags=body.edited_tags,
            annotation_notes=body.annotation_notes,
            annotated_by=body.annotated_by,
            review_status=body.review_status,
            verification_label=verification_label,
            ui_evaluability=ui_evaluability,
            uncertainty_reasons=body.uncertainty_reasons,
            claims=body.claims,
            evidence_steps=body.evidence_steps,
            evidence_note=body.evidence_note,
            rationale=body.rationale,
        )
        return item.to_dict()
    except (FileNotFoundError, KeyError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.delete("/flows/{flow_id}/gold/{requirement_id}")
def delete_gold_requirement(flow_id: str, requirement_id: str) -> dict[str, Any]:
    try:
        req = annotation_service.delete_gold_requirement(flow_id, requirement_id)
        return {
            "requirement_id": req.requirement_id,
            "flow_id": req.flow_id,
            "deleted": True,
        }
    except (FileNotFoundError, KeyError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.delete("/flows/{flow_id}/verification-gold/{requirement_id}")
def delete_verification_gold_item(flow_id: str, requirement_id: str) -> dict[str, Any]:
    try:
        item, deleted_gold = annotation_service.delete_verification_gold_item(flow_id, requirement_id)
        return {
            "requirement_id": item.requirement_id,
            "flow_id": item.flow_id,
            "deleted": True,
            "deleted_gold_requirement": deleted_gold,
        }
    except (FileNotFoundError, KeyError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/tools/rephrase-claim")
def rephrase_claim(body: RephraseClaimRequest) -> dict[str, str]:
    try:
        raw_text = run_gemini(
            _build_claim_rephrase_prompt(body),
            [],
            model_name=body.model_name,
            temperature=body.temperature,
        )
        parsed = parse_json_response(raw_text)
        claim_text = str(parsed.get("claim_text") or parsed.get("claim") or "").strip()
        if not claim_text:
            raise ValueError("Model response did not contain claim_text.")
        return {"claim_text": claim_text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/verify")
def verify_flow(body: VerifyFlowRequest) -> dict[str, Any]:
    try:
        run = verification_service.verify_flow(
            flow_dir=Path(body.flow_dir),
            steps_arg=body.steps,
            max_images=body.max_images,
            image_max_side=body.image_max_side,
            model_name=body.model_name,
            dry_run=body.dry_run,
        )
        if run is None:
            return {
                "status": "dry_run_completed",
                "flow_dir": body.flow_dir,
            }
        return run.to_dict()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
