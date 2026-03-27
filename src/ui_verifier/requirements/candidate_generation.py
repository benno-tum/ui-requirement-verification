from __future__ import annotations

from pathlib import Path
import argparse
import json
from typing import Any, TypeVar

from dotenv import load_dotenv

from ui_verifier.common.flow_utils import (
    find_flow_dirs,
    find_step_images,
    parse_step_number,
    select_requirement_harvest_images,
)
from ui_verifier.common.image_utils import downscale_to_png_bytes
from ui_verifier.common.json_utils import load_json, parse_json_response
from ui_verifier.requirement_inspection.schemas import (
    AnnotationConfidence,
    NonEvaluableReason,
    RequirementInspectionType,
    UiEvaluability,
    VisibleSubtype,
)
from ui_verifier.requirements.prompting import build_prompt
from ui_verifier.requirements.gemini_client import run_gemini
from ui_verifier.requirements.schemas import (
    BenchmarkDecision,
    CandidateOrigin,
    CandidateRequirement,
    CandidateRequirementFile,
    HarvestedRequirement,
    HarvestedRequirementFile,
    RequirementReviewStatus,
    RequirementScope,
    TaskRelevance,
)


load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_INPUT_DIR = BASE_DIR / "data" / "processed" / "flows" / "mind2web"
DEFAULT_OUTPUT_ROOT = BASE_DIR / "data" / "generated" / "candidate_requirements"
DATASET_NAME = "mind2web"

EnumT = TypeVar("EnumT")


def parse_confidence_label(value: Any) -> AnnotationConfidence:
    if not isinstance(value, str):
        return AnnotationConfidence.MEDIUM
    normalized = value.strip().upper()
    if normalized in {"HIGH", "MEDIUM", "LOW"}:
        return AnnotationConfidence(normalized)
    return AnnotationConfidence.MEDIUM


def infer_scope(step_indices: list[int]) -> RequirementScope:
    if len(step_indices) <= 1:
        return RequirementScope.SINGLE_SCREEN
    return RequirementScope.MULTI_SCREEN


def _coerce_enum(value: Any, enum_type: type[EnumT], default: EnumT) -> EnumT:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            try:
                return enum_type(normalized)
            except ValueError:
                pass
    return default


def _normalize_evidence_steps(evidence_steps_raw: Any, allowed_steps: list[int]) -> list[int]:
    allowed_step_set = set(allowed_steps)
    if not isinstance(evidence_steps_raw, list):
        return []

    step_indices: list[int] = []
    for step in evidence_steps_raw:
        try:
            step_int = int(step)
        except (TypeError, ValueError):
            continue
        if step_int in allowed_step_set:
            step_indices.append(step_int)
    return sorted(set(step_indices))


def normalize_model_harvest(
    parsed: dict[str, Any],
    flow_id: str,
    model_name: str,
    prompt_path: Path,
    allowed_steps: list[int],
) -> HarvestedRequirementFile:
    raw_requirements = parsed.get("requirements", [])
    if not isinstance(raw_requirements, list):
        raise ValueError("Parsed model output must contain a list under 'requirements'.")

    requirements: list[HarvestedRequirement] = []

    for i, item in enumerate(raw_requirements, start=1):
        if not isinstance(item, dict):
            continue

        req_id = str(item.get("id") or f"HARV-{i:02d}").strip()
        harvested_text = str(item.get("harvested_text") or item.get("text") or "").strip()
        if not harvested_text:
            continue

        step_indices = _normalize_evidence_steps(item.get("evidence_steps"), allowed_steps)

        requirement = HarvestedRequirement(
            harvest_id=req_id,
            flow_id=flow_id,
            harvested_text=harvested_text,
            requirement_type=_coerce_enum(
                item.get("requirement_type"), RequirementInspectionType, RequirementInspectionType.UNCLEAR
            ),
            ui_evaluability=_coerce_enum(
                item.get("ui_evaluability"), UiEvaluability, UiEvaluability.NOT_UI_VERIFIABLE
            ),
            non_evaluable_reason=_coerce_enum(
                item.get("non_evaluable_reason"), NonEvaluableReason, NonEvaluableReason.NONE
            ),
            visible_subtype=_coerce_enum(
                item.get("visible_subtype"), VisibleSubtype, VisibleSubtype.NONE
            ),
            task_relevance=_coerce_enum(
                item.get("task_relevance"), TaskRelevance, TaskRelevance.MEDIUM
            ),
            step_indices=step_indices,
            rationale=item.get("rationale"),
            visible_core_candidate=item.get("visible_core_candidate"),
            generation_model=model_name,
            generation_prompt_path=prompt_path.name,
            confidence=parse_confidence_label(item.get("confidence")),
        )
        requirements.append(requirement)

    return HarvestedRequirementFile(
        dataset=DATASET_NAME,
        flow_id=flow_id,
        requirements=requirements,
    )


def build_verification_candidates(
    harvest_file: HarvestedRequirementFile,
) -> CandidateRequirementFile:
    requirements: list[CandidateRequirement] = []

    for idx, harvest in enumerate(harvest_file.requirements, start=1):
        candidate_id = f"REQ-{idx:02d}"
        candidate_text = harvest.harvested_text
        candidate_origin = CandidateOrigin.DIRECT_FROM_HARVEST
        benchmark_decision = BenchmarkDecision.DIRECT_INCLUDE
        review_status = RequirementReviewStatus.CANDIDATE
        ui_evaluability = harvest.ui_evaluability
        non_evaluable_reason = harvest.non_evaluable_reason
        excluded_reason: NonEvaluableReason | None = None

        if harvest.ui_evaluability == UiEvaluability.PARTIALLY_UI_VERIFIABLE:
            if harvest.visible_core_candidate:
                candidate_text = harvest.visible_core_candidate
                candidate_origin = CandidateOrigin.VISIBLE_CORE_REWRITE
                benchmark_decision = BenchmarkDecision.REWRITE_TO_VISIBLE_CORE
                ui_evaluability = UiEvaluability.UI_VERIFIABLE
                non_evaluable_reason = NonEvaluableReason.NONE
            else:
                benchmark_decision = BenchmarkDecision.EXCLUDE_FROM_VERIFICATION_BENCHMARK
                review_status = RequirementReviewStatus.REJECTED
                excluded_reason = harvest.non_evaluable_reason
        elif harvest.ui_evaluability == UiEvaluability.NOT_UI_VERIFIABLE:
            benchmark_decision = BenchmarkDecision.EXCLUDE_FROM_VERIFICATION_BENCHMARK
            review_status = RequirementReviewStatus.REJECTED
            excluded_reason = harvest.non_evaluable_reason

        requirement = CandidateRequirement(
            requirement_id=candidate_id,
            flow_id=harvest.flow_id,
            text=candidate_text,
            scope=infer_scope(harvest.step_indices),
            tags=[],
            step_indices=list(harvest.step_indices),
            rationale=harvest.rationale,
            generation_model=harvest.generation_model,
            generation_prompt_path=harvest.generation_prompt_path,
            confidence=harvest.confidence,
            source_harvest_id=harvest.harvest_id,
            candidate_origin=candidate_origin,
            benchmark_decision=benchmark_decision,
            parent_harvest_text=harvest.harvested_text if candidate_origin == CandidateOrigin.VISIBLE_CORE_REWRITE else None,
            requirement_type=harvest.requirement_type,
            ui_evaluability=ui_evaluability,
            non_evaluable_reason=non_evaluable_reason,
            visible_subtype=harvest.visible_subtype,
            task_relevance=harvest.task_relevance,
            excluded_reason=excluded_reason,
            review_status=review_status,
        )
        requirements.append(requirement)

    candidate_file = CandidateRequirementFile(
        dataset=harvest_file.dataset,
        flow_id=harvest_file.flow_id,
        requirements=requirements,
    )
    validate_candidate_consistency(candidate_file, sorted({s for req in harvest_file.requirements for s in req.step_indices}))
    return candidate_file


def validate_candidate_consistency(
    candidate_file: CandidateRequirementFile,
    selected_steps: list[int],
) -> None:
    selected_step_set = set(selected_steps)
    for requirement in candidate_file.requirements:
        if not set(requirement.step_indices).issubset(selected_step_set):
            raise ValueError(
                f"Candidate {requirement.requirement_id} references steps outside the selected set: {requirement.step_indices} vs {selected_steps}"
            )
        if requirement.candidate_origin == CandidateOrigin.VISIBLE_CORE_REWRITE and not requirement.source_harvest_id:
            raise ValueError(
                f"Candidate {requirement.requirement_id} is a visible-core rewrite but has no source_harvest_id"
            )
        if (
            requirement.benchmark_decision == BenchmarkDecision.EXCLUDE_FROM_VERIFICATION_BENCHMARK
            and requirement.excluded_reason is None
        ):
            raise ValueError(
                f"Candidate {requirement.requirement_id} is excluded but has no excluded_reason"
            )


def generate_harvested_for_flow(
    flow_dir: Path,
    output_root: Path,
    steps_arg: str | None,
    max_images: int | None,
    image_max_side: int,
    dry_run: bool,
    model_name: str,
) -> HarvestedRequirementFile | None:
    task_path = flow_dir / "task.json"
    if not task_path.exists():
        raise FileNotFoundError(f"No task.json in {flow_dir}")

    task = load_json(task_path)
    step_paths = find_step_images(flow_dir)
    if not step_paths:
        raise FileNotFoundError(f"No step images in {flow_dir}")

    selected_paths = select_requirement_harvest_images(
        step_paths,
        steps_arg=steps_arg,
        max_images=max_images,
    )
    selected_steps = [parse_step_number(p) for p in selected_paths]

    prompt = build_prompt(task, selected_steps)

    out_dir = output_root / flow_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)

    out_prompt = out_dir / "gemini_prompt.txt"
    out_prompt.write_text(prompt, encoding="utf-8")

    selection_info = {
        "flow_id": flow_dir.name,
        "selected_steps": selected_steps,
        "selected_files": [p.name for p in selected_paths],
        "image_max_side": image_max_side,
        "model": model_name,
    }
    (out_dir / "gemini_selection.json").write_text(
        json.dumps(selection_info, indent=2),
        encoding="utf-8",
    )

    if dry_run:
        print(f"[DRY RUN] {flow_dir.name}")
        print("Selected steps:", selected_steps)
        print("Output dir:", out_dir)
        return None

    image_bytes_list = [downscale_to_png_bytes(p, max_side=image_max_side) for p in selected_paths]
    raw_text = run_gemini(prompt, image_bytes_list, model_name=model_name)

    (out_dir / "requirements_gemini_raw.txt").write_text(raw_text, encoding="utf-8")

    parsed = parse_json_response(raw_text)
    (out_dir / "requirements_gemini.json").write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    harvest_file = normalize_model_harvest(
        parsed=parsed,
        flow_id=flow_dir.name,
        model_name=model_name,
        prompt_path=out_prompt,
        allowed_steps=selected_steps,
    )
    harvest_path = out_dir / "harvested_requirements.json"
    harvest_file.save(harvest_path)

    print(f"[OK] {flow_dir.name} -> {harvest_path}")
    return harvest_file


def process_flow(
    flow_dir: Path,
    output_root: Path,
    steps_arg: str | None,
    max_images: int | None,
    image_max_side: int,
    dry_run: bool,
    model_name: str,
) -> None:
    try:
        harvest_file = generate_harvested_for_flow(
            flow_dir=flow_dir,
            output_root=output_root,
            steps_arg=steps_arg,
            max_images=max_images,
            image_max_side=image_max_side,
            dry_run=dry_run,
            model_name=model_name,
        )
    except FileNotFoundError as exc:
        print(f"[SKIP] {exc}")
        return

    if dry_run or harvest_file is None:
        return

    candidate_file = build_verification_candidates(harvest_file)
    candidate_path = output_root / flow_dir.name / "candidate_requirements.json"
    candidate_file.save(candidate_path)
    print(f"[OK] {flow_dir.name} -> {candidate_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--flow-dir", type=Path, default=None, help="Process exactly one flow folder")
    parser.add_argument("--max-flows", type=int, default=3)
    parser.add_argument("--steps", type=str, default=None, help="Manual step selection, e.g. 1,4,7,10")
    parser.add_argument("--max-images", type=int, default=4, help="Used if --steps is not given")
    parser.add_argument("--image-max-side", type=int, default=1024)
    parser.add_argument("--model", type=str, default="gemini-2.5-flash")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.flow_dir is not None:
        flow_dirs = [args.flow_dir]
    else:
        flow_dirs = find_flow_dirs(args.input_dir)[: args.max_flows]

    if not flow_dirs:
        print("No flow directories found.")
        return

    for flow_dir in flow_dirs:
        process_flow(
            flow_dir=flow_dir,
            output_root=args.output_root,
            steps_arg=args.steps,
            max_images=args.max_images,
            image_max_side=args.image_max_side,
            dry_run=args.dry_run,
            model_name=args.model,
        )


if __name__ == "__main__":
    main()
