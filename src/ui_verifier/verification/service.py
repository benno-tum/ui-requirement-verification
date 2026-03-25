from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from ui_verifier.annotation.service import AnnotationService
from ui_verifier.common.flow_utils import (
    find_step_images,
    parse_step_number,
    select_images,
)
from ui_verifier.common.image_utils import downscale_to_png_bytes
from ui_verifier.common.json_utils import load_json, parse_json_response
from ui_verifier.requirements.gemini_client import run_gemini
from ui_verifier.verification.prompting import build_verification_prompt
from ui_verifier.verification.schemas import (
    EvidenceRef,
    RequirementVerdict,
    VerificationRun,
    VerdictLabel,
)
from ui_verifier.verification.storage import VerificationStorage


def _normalize_label(value: Any) -> VerdictLabel:
    if not isinstance(value, str):
        return VerdictLabel.ABSTAIN

    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "fulfilled": VerdictLabel.FULFILLED,
        "partially_fulfilled": VerdictLabel.PARTIALLY_FULFILLED,
        "partial": VerdictLabel.PARTIALLY_FULFILLED,
        "not_fulfilled": VerdictLabel.NOT_FULFILLED,
        "notfulfilled": VerdictLabel.NOT_FULFILLED,
        "abstain": VerdictLabel.ABSTAIN,
    }
    return mapping.get(normalized, VerdictLabel.ABSTAIN)


def _normalize_confidence(value: Any) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        return None
    value = float(value)
    if not (0.0 <= value <= 1.0):
        return None
    return value


def normalize_verdict(
    parsed: dict[str, Any],
    requirement_id: str,
    allowed_steps: list[int],
) -> RequirementVerdict:
    allowed_step_set = set(allowed_steps)
    label = _normalize_label(parsed.get("label"))
    confidence = _normalize_confidence(parsed.get("confidence"))
    explanation = parsed.get("explanation")

    raw_evidence = parsed.get("evidence", [])
    if not isinstance(raw_evidence, list):
        raw_evidence = []

    evidence: list[EvidenceRef] = []
    for item in raw_evidence:
        if not isinstance(item, dict):
            continue

        try:
            step_index = int(item.get("step_index"))
        except (TypeError, ValueError):
            continue

        if step_index not in allowed_step_set:
            continue

        evidence.append(
            EvidenceRef(
                step_index=step_index,
                reason=item.get("reason"),
                matched_text=item.get("matched_text"),
            )
        )

    if label in {VerdictLabel.FULFILLED, VerdictLabel.PARTIALLY_FULFILLED} and not evidence:
        label = VerdictLabel.ABSTAIN
        explanation = (
            "Model returned a positive verdict without valid evidence on the visible steps."
            if not explanation
            else explanation
        )

    return RequirementVerdict(
        requirement_id=requirement_id,
        label=label,
        evidence=evidence,
        confidence=confidence,
        explanation=explanation,
    )


class VerificationService:
    def __init__(
        self,
        annotation_service: AnnotationService | None = None,
        storage: VerificationStorage | None = None,
    ) -> None:
        self.annotation_service = annotation_service or AnnotationService()
        self.storage = storage or VerificationStorage()

    def verify_flow(
        self,
        *,
        flow_dir: Path,
        steps_arg: str | None = None,
        max_images: int | None = 4,
        image_max_side: int = 1024,
        model_name: str = "gemini-2.5-flash",
        dry_run: bool = False,
    ) -> VerificationRun | None:
        flow_id = flow_dir.name
        task_path = flow_dir / "task.json"
        if not task_path.exists():
            raise FileNotFoundError(f"Missing task.json in {flow_dir}")

        task = load_json(task_path)
        gold_requirements = self.annotation_service.list_gold_requirements(flow_id)
        if not gold_requirements:
            raise ValueError(f"No gold requirements available for flow {flow_id}")

        step_paths = find_step_images(flow_dir)
        if not step_paths:
            raise ValueError(f"No step images found in {flow_dir}")

        selected_paths = select_images(step_paths, steps_arg=steps_arg, max_images=max_images)
        selected_steps = [parse_step_number(p) for p in selected_paths]

        out_dir = self.storage.run_dir(flow_id)
        prompts_dir = out_dir / "prompts"
        raw_dir = out_dir / "raw"
        parsed_dir = out_dir / "parsed"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)
        parsed_dir.mkdir(parents=True, exist_ok=True)

        selection_info = {
            "flow_id": flow_id,
            "selected_steps": selected_steps,
            "selected_files": [p.name for p in selected_paths],
            "image_max_side": image_max_side,
            "model": model_name,
            "gold_requirement_ids": [r.requirement_id for r in gold_requirements],
        }
        (out_dir / "selection.json").write_text(
            json.dumps(selection_info, indent=2),
            encoding="utf-8",
        )

        if dry_run:
            for req in gold_requirements:
                prompt = build_verification_prompt(task, req.text, selected_steps)
                (prompts_dir / f"{req.requirement_id}.txt").write_text(prompt, encoding="utf-8")
            print(f"[DRY RUN] {flow_id}")
            print("Selected steps:", selected_steps)
            print("Prompt dir:", prompts_dir)
            return None

        image_bytes_list = [downscale_to_png_bytes(p, max_side=image_max_side) for p in selected_paths]
        verdicts: list[RequirementVerdict] = []

        for req in gold_requirements:
            prompt = build_verification_prompt(task, req.text, selected_steps)
            (prompts_dir / f"{req.requirement_id}.txt").write_text(prompt, encoding="utf-8")

            raw_text = run_gemini(prompt, image_bytes_list, model_name=model_name)
            (raw_dir / f"{req.requirement_id}.txt").write_text(raw_text, encoding="utf-8")

            parsed = parse_json_response(raw_text)
            (parsed_dir / f"{req.requirement_id}.json").write_text(
                json.dumps(parsed, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            verdict = normalize_verdict(
                parsed=parsed,
                requirement_id=req.requirement_id,
                allowed_steps=selected_steps,
            )
            verdicts.append(verdict)

        run = VerificationRun(
            dataset="mind2web",
            flow_id=flow_id,
            verifier_name=model_name,
            verdicts=verdicts,
        )
        self.storage.save_run(run)
        return run
