from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ui_verifier.annotation.service import AnnotationService
from ui_verifier.api.flow_catalog import BASE_DIR, FlowCatalog
from ui_verifier.verification.service import VerificationService
from ui_verifier.verification.storage import VerificationStorage


app = FastAPI(title="UI Verifier API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

annotation_service = AnnotationService()
verification_storage = VerificationStorage()
verification_service = VerificationService(annotation_service=annotation_service)
flow_catalog = FlowCatalog(
    annotation_storage=annotation_service.storage,
    verification_storage=verification_storage,
)

processed_root = BASE_DIR / "data" / "processed"
if processed_root.exists():
    app.mount("/static", StaticFiles(directory=processed_root), name="static")


class AcceptCandidateRequest(BaseModel):
    edited_text: str | None = None
    edited_step_indices: list[int] | None = None
    edited_tags: list[str] | None = None
    annotation_notes: str | None = None
    annotated_by: str | None = None


class RejectCandidateRequest(BaseModel):
    reason: str | None = None
    annotated_by: str | None = None


class VerifyFlowRequest(BaseModel):
    flow_dir: str
    steps: str | None = None
    max_images: int | None = 4
    image_max_side: int = 1024
    model_name: str = "gemini-2.5-flash"
    dry_run: bool = True


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


@app.get("/flows/{flow_id}/candidates")
def list_candidates(flow_id: str, only_pending: bool = False) -> list[dict[str, Any]]:
    try:
        reqs = annotation_service.list_candidates(flow_id, only_pending=only_pending)
        return [r.to_dict() for r in reqs]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/flows/{flow_id}/gold")
def list_gold_requirements(flow_id: str) -> list[dict[str, Any]]:
    try:
        reqs = annotation_service.list_gold_requirements(flow_id)
        return [r.to_dict() for r in reqs]
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


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
        )
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
