from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ui_verifier.annotation.service import AnnotationService
from ui_verifier.api.flow_catalog import FlowCatalog
from ui_verifier.requirements.candidate_generation import generate_harvested_for_flow
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


@app.get("/flows/{flow_id}/verification/latest")
def get_latest_verification_run(flow_id: str) -> dict[str, Any]:
    try:
        return verification_storage.load_run(flow_id).to_dict()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


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
            edited_step_indices=body.edited_step_indices,
            edited_tags=body.edited_tags,
            annotation_notes=body.annotation_notes,
            annotated_by=body.annotated_by,
            review_status=None,
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
