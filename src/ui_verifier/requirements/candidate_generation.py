from __future__ import annotations

from pathlib import Path
import argparse
import json
from typing import Any, TypeVar
import re

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
from ui_verifier.requirements.prompting import build_candidate_rewrite_prompt, build_prompt, build_pure_prior_harvest_prompt
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
PURE_PRIOR_POOL_PATH = BASE_DIR / "data" / "derived_requirement_priors" / "pure_requirement_pool.json"
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


def _tokenize_for_prior_matching(text: str) -> set[str]:
    return {tok for tok in re.findall(r"[a-z0-9]+", text.lower()) if len(tok) >= 3}


FALLBACK_PURE_PRIOR_POOL: list[dict[str, Any]] = [
    {
        "id": "PURE-FR-001",
        "theme": "discoverability",
        "requirement_type": "FR",
        "ui_evaluability_prior": "PARTIALLY_UI_VERIFIABLE",
        "template": "The system shall support discoverability of relevant items through search and filtering.",
        "visible_core_hint": "search input, filter controls, narrowed result list",
        "typical_ui_signals": ["search bar", "search input", "filter", "calendar", "result list", "events"],
        "domains": ["entertainment", "shopping", "travel", "web"],
    },
    {
        "id": "PURE-FR-002",
        "theme": "inspection",
        "requirement_type": "FR",
        "ui_evaluability_prior": "PARTIALLY_UI_VERIFIABLE",
        "template": "The system shall present result information in a form that supports user inspection and comparison.",
        "visible_core_hint": "list entries with key attributes and action affordances",
        "typical_ui_signals": ["list", "results", "date", "time", "venue", "price", "button", "tickets"],
        "domains": ["entertainment", "shopping", "travel", "web"],
    },
    {
        "id": "PURE-NFR-001",
        "theme": "feedback",
        "requirement_type": "NFR",
        "ui_evaluability_prior": "UI_VERIFIABLE",
        "template": "The system shall provide clear visual feedback when a user selection becomes active.",
        "visible_core_hint": "highlighted active option or updated visible state",
        "typical_ui_signals": ["highlight", "selected", "active", "calendar", "date range", "checked"],
        "domains": ["web", "entertainment", "shopping", "travel"],
    },
    {
        "id": "PURE-NFR-002",
        "theme": "consistency",
        "requirement_type": "NFR",
        "ui_evaluability_prior": "PARTIALLY_UI_VERIFIABLE",
        "template": "The system shall maintain consistency between selected criteria and displayed results.",
        "visible_core_hint": "same chosen context shown later, results reflecting chosen filter",
        "typical_ui_signals": ["selected filter", "date range", "results", "matching", "same context", "carry over"],
        "domains": ["web", "entertainment", "shopping", "travel"],
    },
    {
        "id": "PURE-NFR-003",
        "theme": "guidance",
        "requirement_type": "NFR",
        "ui_evaluability_prior": "UI_VERIFIABLE",
        "template": "The system shall provide clear visual guidance during constrained user interaction.",
        "visible_core_hint": "clear next-step cue or visible filter guidance",
        "typical_ui_signals": ["calendar", "months", "guide", "prompt", "highlight", "selection"],
        "domains": ["web", "entertainment", "shopping", "travel"],
    },
]


def load_pure_prior_pool(path: Path = PURE_PRIOR_POOL_PATH) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if path.exists():
        data = load_json(path)
        file_entries = data.get("entries", [])
        if isinstance(file_entries, list):
            entries.extend(e for e in file_entries if isinstance(e, dict))
    if not entries:
        entries = list(FALLBACK_PURE_PRIOR_POOL)
    return entries


def retrieve_relevant_pure_priors(
    task: dict[str, Any],
    selected_steps: list[int],
    flow_first: HarvestedRequirementFile | None = None,
    top_k: int = 6,
) -> list[dict[str, Any]]:
    entries = load_pure_prior_pool()
    if not entries:
        return []

    flow_hints = []
    if flow_first is not None:
        for req in flow_first.requirements:
            flow_hints.extend([
                req.harvested_text,
                req.visible_core_candidate or "",
                req.requirement_type.value if hasattr(req.requirement_type, 'value') else str(req.requirement_type),
                req.ui_evaluability.value if hasattr(req.ui_evaluability, 'value') else str(req.ui_evaluability),
                req.visible_subtype.value if hasattr(req.visible_subtype, 'value') else str(req.visible_subtype),
            ])

    query_text = " ".join([
        str(task.get("confirmed_task", "")),
        str(task.get("website", "")),
        str(task.get("domain", "")),
        " ".join(str(x) for x in selected_steps),
        " ".join(flow_hints),
    ])
    query_tokens = _tokenize_for_prior_matching(query_text)
    domain = str(task.get("domain", "")).strip().lower()
    website = str(task.get("website", "")).strip().lower()

    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in entries:
        entry_text = " ".join([
            str(entry.get("theme", "")),
            str(entry.get("template", "")),
            str(entry.get("visible_core_hint", "")),
            " ".join(str(x) for x in entry.get("typical_ui_signals", [])),
            " ".join(str(x) for x in entry.get("domains", [])),
        ])
        entry_tokens = _tokenize_for_prior_matching(entry_text)
        overlap = len(query_tokens & entry_tokens)
        score = overlap * 3

        theme = str(entry.get("theme", "")).lower()
        signals = {str(x).lower() for x in entry.get("typical_ui_signals", [])}
        domains = {str(x).lower() for x in entry.get("domains", [])}

        if str(entry.get("requirement_type")) == "NFR":
            score += 1
        if str(entry.get("ui_evaluability_prior")) == "PARTIALLY_UI_VERIFIABLE":
            score += 1
        if domain and domain in domains:
            score += 3
        if website and website in domains:
            score += 1

        # strong heuristic boosts for common UI/flow cues
        if {"search", "events", "calendar", "date", "results", "tickets"} & query_tokens:
            if theme in {"discoverability", "inspection", "feedback", "consistency", "guidance"}:
                score += 2
        if signals & query_tokens:
            score += len(signals & query_tokens) * 2

        scored.append((score, entry))

    scored.sort(key=lambda x: (x[0], str(x[1].get("requirement_type")) == "NFR", str(x[1].get("ui_evaluability_prior")) == "PARTIALLY_UI_VERIFIABLE"), reverse=True)
    selected = [entry for score, entry in scored if score > 0][:top_k]
    if selected:
        return selected

    # fallback: keep a balanced default mix instead of returning nothing
    fallback: list[dict[str, Any]] = []
    wanted_ids = ["PURE-NFR-001", "PURE-NFR-002", "PURE-FR-001", "PURE-FR-002"]
    by_id = {str(e.get("id")): e for e in entries}
    for wanted in wanted_ids:
        if wanted in by_id and len(fallback) < top_k:
            fallback.append(by_id[wanted])
    if fallback:
        return fallback[:top_k]
    return [entry for _, entry in scored[:top_k]]


def _normalize_requirement_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def merge_harvested_sets(
    flow_first: HarvestedRequirementFile,
    pure_prior: HarvestedRequirementFile | None,
) -> tuple[HarvestedRequirementFile, dict[str, Any]]:
    merged: list[HarvestedRequirement] = []
    seen: dict[str, HarvestedRequirement] = {}
    report = {
        "flow_first_count": len(flow_first.requirements),
        "pure_prior_count": len(pure_prior.requirements) if pure_prior else 0,
        "duplicates_dropped": [],
    }

    def add_req(req: HarvestedRequirement) -> None:
        key = _normalize_requirement_key(req.harvested_text)
        existing = seen.get(key)
        if existing is None:
            seen[key] = req
            merged.append(req)
            return
        report["duplicates_dropped"].append({
            "kept": existing.harvest_id,
            "dropped": req.harvest_id,
            "text": req.harvested_text,
        })

    for idx, req in enumerate(flow_first.requirements, start=1):
        req.harvest_id = f"HARV-{idx:02d}"
        if not req.source_strategy:
            req.source_strategy = "flow_first"
        add_req(req)

    if pure_prior is not None:
        start = len(merged) + 1
        for offset, req in enumerate(pure_prior.requirements, start=start):
            req.harvest_id = f"HARV-{offset:02d}"
            if not req.source_strategy:
                req.source_strategy = "pure_prior"
            add_req(req)

    merged_file = HarvestedRequirementFile(
        dataset=flow_first.dataset,
        flow_id=flow_first.flow_id,
        requirements=merged,
    )
    report["merged_count"] = len(merged)
    return merged_file, report


def _run_harvest_pass(
    *,
    prompt: str,
    selected_paths: list[Path],
    selected_steps: list[int],
    image_max_side: int,
    model_name: str,
    temperature: float,
    output_dir: Path,
    prompt_filename: str,
    raw_filename: str,
    parsed_filename: str,
    saved_filename: str | None,
    source_strategy: str,
    prior_source_ids: list[str] | None = None,
) -> HarvestedRequirementFile:
    prompt_path = output_dir / prompt_filename
    prompt_path.write_text(prompt, encoding="utf-8")
    image_bytes_list = [downscale_to_png_bytes(p, max_side=image_max_side) for p in selected_paths]
    raw_text = run_gemini(prompt, image_bytes_list, model_name=model_name, temperature=temperature)
    (output_dir / raw_filename).write_text(raw_text, encoding="utf-8")
    parsed = parse_json_response(raw_text)
    (output_dir / parsed_filename).write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
    harvest_file = normalize_model_harvest(parsed=parsed, flow_id=output_dir.name, model_name=model_name, prompt_path=prompt_path, allowed_steps=selected_steps)
    for req in harvest_file.requirements:
        req.source_strategy = source_strategy
        req.prior_source_ids = list(prior_source_ids or [])
    if saved_filename is not None:
        harvest_file.save(output_dir / saved_filename)
    return harvest_file


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





def normalize_model_candidates(
    parsed: dict[str, Any],
    harvest_file: HarvestedRequirementFile,
    model_name: str,
    prompt_path: Path,
) -> CandidateRequirementFile:
    raw_requirements = parsed.get("requirements", [])
    if not isinstance(raw_requirements, list):
        raise ValueError("Parsed model output must contain a list under 'requirements'.")

    harvest_by_id = {req.harvest_id: req for req in harvest_file.requirements}
    requirements: list[CandidateRequirement] = []

    for idx, item in enumerate(raw_requirements, start=1):
        if not isinstance(item, dict):
            continue

        source_harvest_id = str(item.get("source_harvest_id") or "").strip()
        if not source_harvest_id or source_harvest_id not in harvest_by_id:
            continue

        harvest = harvest_by_id[source_harvest_id]
        candidate_text = str(item.get("candidate_text") or "").strip()
        if not candidate_text:
            continue

        candidate_id = str(item.get("id") or f"REQ-{idx:02d}").strip()
        candidate_origin = _coerce_enum(
            item.get("candidate_origin"),
            CandidateOrigin,
            CandidateOrigin.VISIBLE_CORE_REWRITE if candidate_text != harvest.harvested_text else CandidateOrigin.DIRECT_FROM_HARVEST,
        )
        benchmark_decision = _coerce_enum(
            item.get("benchmark_decision"),
            BenchmarkDecision,
            BenchmarkDecision.DIRECT_INCLUDE,
        )

        ui_evaluability = _coerce_enum(
            item.get("ui_evaluability"),
            UiEvaluability,
            UiEvaluability.UI_VERIFIABLE,
        )
        visible_subtype = _coerce_enum(
            item.get("visible_subtype"),
            VisibleSubtype,
            harvest.visible_subtype if harvest.visible_subtype != VisibleSubtype.NONE else VisibleSubtype.TEXT_OR_ELEMENT_PRESENCE,
        )
        requirement_type = _coerce_enum(
            item.get("requirement_type"),
            RequirementInspectionType,
            harvest.requirement_type,
        )

        review_status = RequirementReviewStatus.CANDIDATE
        excluded_reason: NonEvaluableReason | None = None
        non_evaluable_reason = NonEvaluableReason.NONE

        if benchmark_decision == BenchmarkDecision.EXCLUDE_FROM_VERIFICATION_BENCHMARK:
            review_status = RequirementReviewStatus.REJECTED
            ui_evaluability = UiEvaluability.NOT_UI_VERIFIABLE
            visible_subtype = VisibleSubtype.NONE
            excluded_reason = harvest.non_evaluable_reason
            if excluded_reason == NonEvaluableReason.NONE:
                excluded_reason = NonEvaluableReason.TOO_ABSTRACT
            non_evaluable_reason = excluded_reason
        elif ui_evaluability == UiEvaluability.PARTIALLY_UI_VERIFIABLE:
            benchmark_decision = BenchmarkDecision.REWRITE_TO_VISIBLE_CORE
            candidate_origin = CandidateOrigin.VISIBLE_CORE_REWRITE
            non_evaluable_reason = harvest.non_evaluable_reason if harvest.non_evaluable_reason != NonEvaluableReason.NONE else NonEvaluableReason.BUSINESS_RULE_NOT_VISIBLE
        else:
            ui_evaluability = UiEvaluability.UI_VERIFIABLE
            non_evaluable_reason = NonEvaluableReason.NONE

        normalization_notes = str(item.get("normalization_notes") or "").strip()
        rationale_parts = [part for part in [normalization_notes, harvest.rationale] if part]
        rationale = "\n\n".join(rationale_parts) or None

        requirement = CandidateRequirement(
            requirement_id=candidate_id,
            flow_id=harvest.flow_id,
            text=candidate_text,
            scope=infer_scope(harvest.step_indices),
            tags=[],
            step_indices=list(harvest.step_indices),
            rationale=rationale,
            generation_model=model_name,
            generation_prompt_path=prompt_path.name,
            confidence=harvest.confidence,
            source_harvest_id=harvest.harvest_id,
            candidate_origin=candidate_origin,
            benchmark_decision=benchmark_decision,
            parent_harvest_text=harvest.harvested_text if candidate_origin == CandidateOrigin.VISIBLE_CORE_REWRITE else None,
            requirement_type=requirement_type,
            ui_evaluability=ui_evaluability,
            non_evaluable_reason=non_evaluable_reason,
            visible_subtype=visible_subtype,
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


def rewrite_verification_candidates(
    harvest_file: HarvestedRequirementFile,
    output_dir: Path,
    model_name: str,
    temperature: float = 0.2,
) -> CandidateRequirementFile:
    prompt = build_candidate_rewrite_prompt(harvest_file.to_dict())
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = output_dir / "candidate_rewrite_prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")

    raw_text = run_gemini(prompt, [], model_name=model_name, temperature=temperature)
    (output_dir / "candidate_rewrite_raw.txt").write_text(raw_text, encoding="utf-8")

    parsed = parse_json_response(raw_text)
    (output_dir / "candidate_rewrite_parsed.json").write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return normalize_model_candidates(
        parsed=parsed,
        harvest_file=harvest_file,
        model_name=model_name,
        prompt_path=prompt_path,
    )
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
    temperature: float = 0.6,
    hybrid_mode: bool = False,
    pure_prior_top_k: int = 6,
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

    selection_info = {
        "flow_id": flow_dir.name,
        "selected_steps": selected_steps,
        "selected_files": [p.name for p in selected_paths],
        "image_max_side": image_max_side,
        "model": model_name,
        "temperature": temperature,
        "hybrid_mode": hybrid_mode,
        "pure_prior_top_k": pure_prior_top_k,
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

    flow_first = _run_harvest_pass(
        prompt=prompt,
        selected_paths=selected_paths,
        selected_steps=selected_steps,
        image_max_side=image_max_side,
        model_name=model_name,
        temperature=temperature,
        output_dir=out_dir,
        prompt_filename="gemini_prompt.txt",
        raw_filename="requirements_gemini_raw.txt",
        parsed_filename="requirements_gemini.json",
        saved_filename="harvested_requirements_flow_first.json" if hybrid_mode else None,
        source_strategy="flow_first",
    )

    final_harvest = flow_first
    if hybrid_mode:
        retrieved = retrieve_relevant_pure_priors(task, selected_steps, flow_first=flow_first, top_k=pure_prior_top_k)
        (out_dir / "pure_prior_retrieved.json").write_text(json.dumps({"entries": retrieved}, indent=2, ensure_ascii=False), encoding="utf-8")

        if retrieved:
            pure_prompt = build_pure_prior_harvest_prompt(task, selected_steps, flow_first.to_dict(), retrieved)
            pure_prior_file = _run_harvest_pass(
                prompt=pure_prompt,
                selected_paths=selected_paths,
                selected_steps=selected_steps,
                image_max_side=image_max_side,
                model_name=model_name,
                temperature=max(0.4, min(temperature, 0.7)),
                output_dir=out_dir,
                prompt_filename="pure_prior_harvest_prompt.txt",
                raw_filename="pure_prior_harvest_raw.txt",
                parsed_filename="pure_prior_harvest_parsed.json",
                saved_filename="harvested_requirements_pure_prior.json",
                source_strategy="pure_prior",
                prior_source_ids=[str(entry.get("id")) for entry in retrieved if entry.get("id")],
            )
            final_harvest, merge_report = merge_harvested_sets(flow_first, pure_prior_file)
        else:
            merge_report = {"flow_first_count": len(flow_first.requirements), "pure_prior_count": 0, "merged_count": len(flow_first.requirements), "duplicates_dropped": []}

        (out_dir / "hybrid_harvest_merge_report.json").write_text(json.dumps(merge_report, indent=2, ensure_ascii=False), encoding="utf-8")

    harvest_path = out_dir / "harvested_requirements.json"
    final_harvest.save(harvest_path)

    print(f"[OK] {flow_dir.name} -> {harvest_path}")
    return final_harvest


def process_flow(
    flow_dir: Path,
    output_root: Path,
    steps_arg: str | None,
    max_images: int | None,
    image_max_side: int,
    dry_run: bool,
    model_name: str,
    candidate_model_name: str,
    harvest_temperature: float,
    hybrid_mode: bool,
    pure_prior_top_k: int,
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
            temperature=harvest_temperature,
            hybrid_mode=hybrid_mode,
            pure_prior_top_k=pure_prior_top_k,
        )
    except FileNotFoundError as exc:
        print(f"[SKIP] {exc}")
        return

    if dry_run or harvest_file is None:
        return

    candidate_path = output_root / flow_dir.name / "candidate_requirements.json"
    try:
        candidate_file = rewrite_verification_candidates(
            harvest_file=harvest_file,
            output_dir=output_root / flow_dir.name,
            model_name=candidate_model_name,
        )
    except Exception as exc:
        print(f"[WARN] Candidate rewrite failed for {flow_dir.name}: {exc}")
        candidate_file = build_verification_candidates(harvest_file)
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
    parser.add_argument("--image-max-side", type=int, default=1280)
    parser.add_argument("--model", type=str, default="gemini-2.5-flash")
    parser.add_argument("--harvest-temperature", type=float, default=0.7)
    parser.add_argument("--candidate-model", type=str, default="gemini-2.5-flash-lite")
    parser.add_argument("--hybrid-mode", action="store_true")
    parser.add_argument("--pure-prior-top-k", type=int, default=6)
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
            candidate_model_name=args.candidate_model,
            harvest_temperature=args.harvest_temperature,
            hybrid_mode=args.hybrid_mode,
            pure_prior_top_k=args.pure_prior_top_k,
        )


if __name__ == "__main__":
    main()
