from __future__ import annotations

from collections import deque
import json
import re
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Any
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ui_verifier.annotation.service import AnnotationService
from ui_verifier.model_config import all_model_role_configs, model_config_path, model_name_for, temperature_for
from ui_verifier.api.flow_catalog import FlowCatalog
from ui_verifier.requirement_inspection.schemas import UiEvaluability
from ui_verifier.requirements.candidate_generation import generate_harvested_for_flow
from ui_verifier.requirements.gemini_client import run_gemini
from ui_verifier.requirements.gemini_usage import read_usage_summary, usage_log_path, usage_summary_path
from ui_verifier.requirements.schemas import RequirementReviewStatus
from ui_verifier.common.json_utils import parse_json_response
from ui_verifier.evaluation.prediction_coverage import coverage_for_files
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
VERIFICATION_PIPELINE_ROOT = Path(__file__).resolve().parents[3] / "data" / "generated" / "verification_pipeline"
BASE_DIR = Path(__file__).resolve().parents[3]
GENERATED_ROOT = BASE_DIR / "data" / "generated"
REQUIREMENTS_GOLD_ROOT = BASE_DIR / "data" / "annotations" / "requirements_gold"
VERIFICATION_GOLD_ROOT = BASE_DIR / "data" / "annotations" / "verification_gold"
RUN_OUTPUT_DIR_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")
RUN_JOBS: dict[str, dict[str, Any]] = {}
RUN_JOBS_LOCK = threading.Lock()

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
    model_name: str = model_name_for("verification")
    dry_run: bool = True


class GenerateHarvestedRequest(BaseModel):
    max_images: int | None = 6
    image_max_side: int = 1280
    model_name: str = model_name_for("api_requirement_harvest")
    temperature: float = temperature_for("api_requirement_harvest")
    hybrid_mode: bool = False
    pure_prior_top_k: int = 6


class RebuildCandidatesRequest(BaseModel):
    candidate_model_name: str = model_name_for("candidate_rewrite")
    allow_overwrite_with_gold: bool = False


class RephraseClaimRequest(BaseModel):
    requirement_text: str
    claim_text: str
    feedback: str
    claim_status: str | None = None
    claim_type: str | None = None
    importance: str | None = None
    model_name: str = model_name_for("claim_rephrase")
    temperature: float = temperature_for("claim_rephrase")


class StartPipelineRunRequest(BaseModel):
    verifier: str = "deterministic"
    verifier_model: str = model_name_for("demo_image_verifier")
    retriever: str = "lexical"
    requirements_source: str = "accepted"
    top_k: int = 3
    max_images: int = 6
    max_gemini_api_calls: int = 0
    use_cache: bool = True
    output_dir_name: str = "ui_verification_runs"


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BASE_DIR.resolve()))
    except ValueError:
        return str(path)


def _require_under(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Path escapes allowed root: {_repo_relative(path)}") from exc
    return resolved


def _run_id_for_path(path: Path) -> str:
    return _repo_relative(path)


def _path_for_run_id(run_id: str) -> Path:
    if not run_id or "\x00" in run_id:
        raise HTTPException(status_code=400, detail="Invalid run id.")
    path = (BASE_DIR / run_id).resolve()
    _require_under(path, GENERATED_ROOT)
    if path.suffix != ".json":
        raise HTTPException(status_code=400, detail="Run id must point to a JSON file.")
    return path


def _load_json_object(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _iter_verification_run_paths() -> list[Path]:
    roots = [
        VERIFICATION_PIPELINE_ROOT,
        DEMO_VERIFICATION_ROOT,
        *(path for path in GENERATED_ROOT.glob("diagnosis*") if path.is_dir()),
        *(path for path in GENERATED_ROOT.glob("benchmark*") if path.is_dir()),
        GENERATED_ROOT / "ui_verification_runs",
    ]
    paths: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("*.json"):
            if path.name.startswith("metrics"):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            paths.append(path)
    return paths


def _metrics_available_for(path: Path) -> bool:
    return any(path.parent.glob("*metrics*.json"))


def _run_entry_from_data(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    results = data.get("results") if isinstance(data.get("results"), list) else []
    label_distribution = metadata.get("label_distribution")
    if not isinstance(label_distribution, dict):
        label_distribution = {}
        for result in results:
            if not isinstance(result, dict):
                continue
            label = str(result.get("final_label") or "UNKNOWN")
            label_distribution[label] = int(label_distribution.get(label, 0)) + 1

    return {
        "run_id": _run_id_for_path(path),
        "flow_id": data.get("flow_id"),
        "path": _repo_relative(path),
        "source": path.parent.name,
        "run_folder": _repo_relative(path.parent),
        "mtime": path.stat().st_mtime,
        "timestamp": metadata.get("created_at") or metadata.get("run_mtime") or path.stat().st_mtime,
        "verifier": metadata.get("verifier") or metadata.get("run_source") or metadata.get("pipeline") or "unknown",
        "verifier_model": metadata.get("verifier_model"),
        "retriever": metadata.get("selected_retriever") or metadata.get("retriever") or metadata.get("requested_retriever"),
        "requirements_count": metadata.get("requirements_count") or len(results),
        "label_distribution": label_distribution,
        "metrics_available": _metrics_available_for(path),
    }


def discover_pipeline_runs(flow_id: str) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for path in _iter_verification_run_paths():
        data = _load_json_object(path)
        if not data or data.get("flow_id") != flow_id or not isinstance(data.get("results"), list):
            continue
        runs.append(_run_entry_from_data(path, data))
    runs.sort(key=lambda item: float(item.get("mtime") or 0.0), reverse=True)
    return runs


def _safe_output_dir(name: str) -> Path:
    normalized = name.strip()
    if not RUN_OUTPUT_DIR_RE.fullmatch(normalized):
        raise HTTPException(
            status_code=400,
            detail="Output directory name may contain only letters, numbers, dot, underscore, and hyphen.",
        )
    return _require_under(GENERATED_ROOT / normalized, GENERATED_ROOT)


def build_pipeline_run_command(flow_id: str, body: StartPipelineRunRequest, *, job_id: str | None = None) -> tuple[list[str], Path]:
    verifier = body.verifier.strip()
    if verifier == "deterministic_rule_based":
        verifier = "deterministic"
    if verifier not in {"deterministic", "gemini-image"}:
        raise HTTPException(status_code=400, detail="verifier must be deterministic_rule_based or gemini-image.")
    if body.retriever != "lexical":
        raise HTTPException(status_code=400, detail="Only lexical retriever is supported from the UI for now.")
    if body.requirements_source not in {"accepted", "benchmark"}:
        raise HTTPException(status_code=400, detail="requirements_source must be accepted or benchmark.")
    if body.top_k < 1 or body.top_k > 20:
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 20.")
    if body.max_images < 1 or body.max_images > 20:
        raise HTTPException(status_code=400, detail="max_images must be between 1 and 20.")
    if body.max_gemini_api_calls < -1 or body.max_gemini_api_calls > 1000:
        raise HTTPException(status_code=400, detail="max_gemini_api_calls must be -1 or between 0 and 1000.")
    if verifier == "gemini-image" and body.max_gemini_api_calls == 0:
        raise HTTPException(status_code=400, detail="Gemini runs require max_gemini_api_calls greater than 0 or -1.")

    _, flow_dir = flow_catalog.resolve_flow(flow_id)
    flow_dir = _require_under(flow_dir, BASE_DIR / "data")
    if body.requirements_source == "benchmark":
        requirements_path = VERIFICATION_GOLD_ROOT / flow_id / "verification_gold.json"
    else:
        requirements_path = REQUIREMENTS_GOLD_ROOT / flow_id / "gold_requirements.json"
        if not requirements_path.exists():
            requirements_path = VERIFICATION_GOLD_ROOT / flow_id / "verification_gold.json"
    if not requirements_path.exists():
        raise HTTPException(status_code=404, detail=f"No requirements file found for {flow_id}.")
    requirements_path = _require_under(requirements_path, BASE_DIR / "data")

    output_dir = _safe_output_dir(body.output_dir_name)
    output_path = _require_under(output_dir / f"{flow_id}.json", output_dir)
    cache_dir = _require_under(output_dir / "cache", output_dir)
    cache_name = f"{flow_id}_gemini_image_claims.json" if body.use_cache else f"{flow_id}_{job_id or 'run'}_gemini_image_claims.json"
    cache_path = _require_under(cache_dir / cache_name, cache_dir)

    command = [
        sys.executable,
        str(BASE_DIR / "scripts" / "run_verification_pipeline.py"),
        "--flow-dir",
        str(flow_dir),
        "--requirements",
        str(requirements_path),
        "--requirements-source",
        body.requirements_source,
        "--out",
        str(output_path),
        "--retriever",
        body.retriever,
        "--top-k",
        str(body.top_k),
        "--verifier",
        verifier,
        "--max-verifier-images",
        str(body.max_images),
        "--max-gemini-api-calls",
        str(body.max_gemini_api_calls),
        "--verifier-cache",
        str(cache_path),
        "--no-llm-claim-fallback",
    ]
    if verifier == "gemini-image":
        command.extend(["--verifier-model", body.verifier_model.strip() or model_name_for("demo_image_verifier")])
    return command, output_path


def _run_pipeline_job(job_id: str, command: list[str], output_path: Path) -> None:
    with RUN_JOBS_LOCK:
        job = RUN_JOBS[job_id]
        job["status"] = "running"
        job["started_at"] = time.time()
    try:
        process = subprocess.Popen(
            command,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False,
            bufsize=1,
        )
        with RUN_JOBS_LOCK:
            RUN_JOBS[job_id]["pid"] = process.pid
        assert process.stdout is not None
        for line in process.stdout:
            with RUN_JOBS_LOCK:
                RUN_JOBS[job_id]["log"].append(line.rstrip())
        return_code = process.wait()
        with RUN_JOBS_LOCK:
            RUN_JOBS[job_id]["completed_at"] = time.time()
            RUN_JOBS[job_id]["return_code"] = return_code
            RUN_JOBS[job_id]["output_path"] = _repo_relative(output_path) if output_path.exists() else None
            RUN_JOBS[job_id]["status"] = "completed" if return_code == 0 else "failed"
    except Exception as exc:
        with RUN_JOBS_LOCK:
            RUN_JOBS[job_id]["completed_at"] = time.time()
            RUN_JOBS[job_id]["status"] = "failed"
            RUN_JOBS[job_id]["error"] = str(exc)
            RUN_JOBS[job_id]["log"].append(str(exc))


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


@app.get("/gemini-usage")
def gemini_usage() -> dict[str, Any]:
    summary = read_usage_summary()
    return {
        **summary,
        "usage_log_path": str(usage_log_path()),
        "usage_summary_path": str(usage_summary_path()),
    }


@app.get("/model-config")
def model_config() -> dict[str, Any]:
    return {
        "config_path": str(model_config_path()),
        "roles": all_model_role_configs(),
    }


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


def _result_evidence_steps(result: dict[str, Any]) -> list[int]:
    steps: list[int] = []
    seen: set[int] = set()
    for item in result.get("evidence", []):
        if not isinstance(item, dict):
            continue
        try:
            step = int(item.get("step_index"))
        except (TypeError, ValueError):
            continue
        if step >= 0 and step not in seen:
            seen.add(step)
            steps.append(step)
    return steps


def _verification_pipeline_summary(flow_id: str, data: dict[str, Any], path: Path) -> None:
    results = data.get("results") if isinstance(data.get("results"), list) else []
    metadata = data.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        return

    label_distribution: dict[str, int] = {}
    claim_status_distribution: dict[str, int] = {}
    claim_count = 0
    for result in results:
        if not isinstance(result, dict):
            continue
        label = str(result.get("final_label") or "UNKNOWN")
        label_distribution[label] = label_distribution.get(label, 0) + 1
        claims = result.get("claims") if isinstance(result.get("claims"), list) else []
        claim_count += len(claims)
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            status = str(claim.get("status") or "UNKNOWN")
            claim_status_distribution[status] = claim_status_distribution.get(status, 0) + 1

    metadata.setdefault("run_path", str(path))
    metadata.setdefault("run_source", "verification_pipeline")
    metadata.setdefault("run_mtime", path.stat().st_mtime)
    metadata.setdefault("requirements_count", len(results))
    metadata.setdefault("claim_count", claim_count)
    metadata.setdefault("label_distribution", label_distribution)
    metadata.setdefault("claim_status_distribution", claim_status_distribution)
    verification_gold_path = VERIFICATION_GOLD_ROOT / flow_id / "verification_gold.json"
    if verification_gold_path.exists() and "prediction_coverage" not in metadata:
        metadata["prediction_coverage"] = coverage_for_files(verification_gold_path, path).to_dict()

    if "reference_comparison" in metadata:
        return

    try:
        reference_items = annotation_service.list_verification_gold(flow_id)
    except FileNotFoundError:
        return

    reference_by_id = {item.requirement_id: item for item in reference_items}
    comparison_items: list[dict[str, Any]] = []
    matches = 0
    compared = 0
    for result in results:
        if not isinstance(result, dict):
            continue
        requirement_id = str(result.get("requirement_id") or "")
        reference = reference_by_id.get(requirement_id)
        predicted_label = result.get("final_label")
        reference_label = reference.verification_label.value if reference and reference.verification_label else None
        matches_reference = predicted_label == reference_label if reference_label is not None else None
        if reference_label is not None:
            compared += 1
            if matches_reference:
                matches += 1
        comparison_items.append(
            {
                "requirement_id": requirement_id,
                "predicted_label": predicted_label,
                "reference_label": reference_label,
                "matches_reference": matches_reference,
                "predicted_evidence_steps": _result_evidence_steps(result),
                "reference_evidence_steps": reference.evidence_steps if reference else [],
            }
        )

    metadata["reference_comparison"] = {
        "summary": {
            "compared_items": compared,
            "matches": matches,
            "accuracy_on_matched_ids": None if compared == 0 else matches / compared,
            "missing_reference_for_predictions": sum(1 for item in comparison_items if item["reference_label"] is None),
        },
        "items": comparison_items,
    }


@app.get("/flows/{flow_id}/verification-pipeline/latest")
def get_latest_verification_pipeline_run(flow_id: str) -> dict[str, Any]:
    for run in discover_pipeline_runs(flow_id):
        path = _path_for_run_id(str(run["run_id"]))
        data = _load_json_object(path)
        if data is None:
            continue
        _verification_pipeline_summary(flow_id, data, path)
        return data
    raise HTTPException(status_code=404, detail=f"Verification pipeline run not found for flow {flow_id}")


@app.get("/flows/{flow_id}/verification-pipeline/runs")
def list_verification_pipeline_runs(flow_id: str) -> dict[str, Any]:
    return {"flow_id": flow_id, "runs": discover_pipeline_runs(flow_id)}


@app.get("/flows/{flow_id}/verification-pipeline/run")
def get_verification_pipeline_run(flow_id: str, run_id: str) -> dict[str, Any]:
    path = _path_for_run_id(run_id)
    data = _load_json_object(path)
    if data is None or data.get("flow_id") != flow_id or not isinstance(data.get("results"), list):
        raise HTTPException(status_code=404, detail=f"Verification pipeline run not found: {run_id}")
    _verification_pipeline_summary(flow_id, data, path)
    return data


@app.post("/flows/{flow_id}/verification-pipeline/start")
def start_verification_pipeline_run(flow_id: str, body: StartPipelineRunRequest) -> dict[str, Any]:
    job_id = uuid.uuid4().hex
    command, output_path = build_pipeline_run_command(flow_id, body, job_id=job_id)
    with RUN_JOBS_LOCK:
        RUN_JOBS[job_id] = {
            "job_id": job_id,
            "flow_id": flow_id,
            "status": "not_started",
            "created_at": time.time(),
            "command": command,
            "output_path": _repo_relative(output_path),
            "log": deque(maxlen=200),
            "return_code": None,
            "pid": None,
        }
    thread = threading.Thread(target=_run_pipeline_job, args=(job_id, command, output_path), daemon=True)
    thread.start()
    return get_verification_pipeline_job(job_id)


@app.get("/verification-pipeline/jobs/{job_id}")
def get_verification_pipeline_job(job_id: str) -> dict[str, Any]:
    with RUN_JOBS_LOCK:
        job = RUN_JOBS.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Pipeline job not found: {job_id}")
        return {
            **{key: value for key, value in job.items() if key not in {"log", "command"}},
            "command": list(job.get("command") or []),
            "recent_log_lines": list(job.get("log") or []),
        }


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
