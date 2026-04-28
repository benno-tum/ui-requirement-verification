from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from enum import Enum
import json
from pathlib import Path
import re
import subprocess
from typing import Any, TypeVar

from ui_verifier.common.json_utils import load_json, parse_json_response
from ui_verifier.requirement_inspection.schemas import (
    AnnotationConfidence,
    NonEvaluableReason,
    RequirementInspectionType,
    UiEvaluability,
    VisibleSubtype,
)
from ui_verifier.requirements.prompting import build_contrastive_from_gold_prompt
from ui_verifier.requirements.schemas import GoldRequirementFile, GroundingScope, RequirementReviewStatus


BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_GOLD_ROOT = BASE_DIR / "data" / "annotations" / "requirements_gold"
DEFAULT_FLOW_ROOT = BASE_DIR / "data" / "processed" / "flows" / "mind2web"
DEFAULT_CONTEXT_ROOT = BASE_DIR / "data" / "generated" / "candidate_requirements"
DEFAULT_OUTPUT_ROOT = BASE_DIR / "data" / "generated" / "contrastive_candidates"
DATASET_NAME = "mind2web"
MANUAL_BUNDLE_DIRNAME = "manual_contrastive_bundle"

EnumT = TypeVar("EnumT")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _require_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("optional text fields must be strings or None")
    value = value.strip()
    return value or None


def _normalize_summary(values: list[Any] | None) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _copy_prompt_to_clipboard(prompt: str) -> bool:
    clipboard_commands = (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"])
    for command in clipboard_commands:
        try:
            subprocess.run(command, input=prompt.encode("utf-8"), check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    return False


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


def _parse_enum(value: Any, enum_type: type[EnumT]) -> EnumT | None:
    if isinstance(value, enum_type):
        return value
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return enum_type(normalized)
    except ValueError:
        return None


def parse_confidence_label(value: Any) -> AnnotationConfidence:
    if not isinstance(value, str):
        return AnnotationConfidence.MEDIUM
    normalized = value.strip().upper()
    if normalized in {"HIGH", "MEDIUM", "LOW"}:
        return AnnotationConfidence(normalized)
    return AnnotationConfidence.MEDIUM


def _normalize_text_for_similarity(text: str) -> str:
    normalized = text.lower().strip()
    normalized = re.sub(r"^the system shall\s+", "", normalized)
    normalized = normalized.replace("/", " ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\b(a|an|the)\b", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _text_similarity(a: str, b: str) -> float:
    normalized_a = _normalize_text_for_similarity(a)
    normalized_b = _normalize_text_for_similarity(b)
    if not normalized_a or not normalized_b:
        return 0.0
    return SequenceMatcher(None, normalized_a, normalized_b).ratio()


def _texts_too_similar(a: str, b: str, *, strict: bool) -> bool:
    normalized_a = _normalize_text_for_similarity(a)
    normalized_b = _normalize_text_for_similarity(b)
    if not normalized_a or not normalized_b:
        return False
    if normalized_a == normalized_b:
        return True

    similarity = SequenceMatcher(None, normalized_a, normalized_b).ratio()
    if similarity >= (0.94 if strict else 0.88):
        return True

    tokens_a = set(normalized_a.split())
    tokens_b = set(normalized_b.split())
    if not tokens_a or not tokens_b:
        return False

    overlap = len(tokens_a & tokens_b) / max(1, min(len(tokens_a), len(tokens_b)))
    return overlap >= (0.92 if strict else 0.82)


def _default_non_evaluable_reason(ui_evaluability: UiEvaluability) -> NonEvaluableReason:
    if ui_evaluability == UiEvaluability.UI_VERIFIABLE:
        return NonEvaluableReason.NONE
    if ui_evaluability == UiEvaluability.PARTIALLY_UI_VERIFIABLE:
        return NonEvaluableReason.BUSINESS_RULE_NOT_VISIBLE
    return NonEvaluableReason.TOO_ABSTRACT


def _relative_prompt_path(prompt_path: Path, output_dir: Path) -> str:
    try:
        return str(prompt_path.relative_to(output_dir))
    except ValueError:
        return prompt_path.name


class IntendedLabel(str, Enum):
    PARTIALLY_FULFILLED = "partially_fulfilled"
    ABSTAIN = "abstain"
    NOT_FULFILLED = "not_fulfilled"


class MutationFamily(str, Enum):
    PERSISTENCE_EXTENSION = "persistence_extension"
    EXTERNAL_EFFECT_EXTENSION = "external_effect_extension"
    POLICY_OR_ROLE_EXTENSION = "policy_or_role_extension"
    HIDDEN_STATE_EXTENSION = "hidden_state_extension"
    COMPLETENESS_OR_UNIVERSAL_QUANTIFIER = "completeness_or_universal_quantifier"
    MISSING_VISIBLE_STEP = "missing_visible_step"
    STRONGER_VISIBLE_CONSTRAINT = "stronger_visible_constraint"
    CROSS_SCREEN_CONSISTENCY_EXTENSION = "cross_screen_consistency_extension"
    NEARBY_CAPABILITY_VARIANT = "nearby_capability_variant"


@dataclass(slots=True)
class ContrastiveCandidateRequirement:
    requirement_id: str
    flow_id: str
    text: str
    source_gold_requirement_id: str
    source_gold_text: str
    mutation_family: MutationFamily
    intended_label: IntendedLabel
    generation_rationale: str | None = None
    review_status: RequirementReviewStatus = RequirementReviewStatus.CANDIDATE
    generation_model: str | None = None
    generation_prompt_path: str | None = None
    grounding_scope: GroundingScope = GroundingScope.INDIRECT_FLOW_GROUNDED
    requirement_type: RequirementInspectionType = RequirementInspectionType.UNCLEAR
    ui_evaluability: UiEvaluability = UiEvaluability.PARTIALLY_UI_VERIFIABLE
    non_evaluable_reason: NonEvaluableReason = NonEvaluableReason.BUSINESS_RULE_NOT_VISIBLE
    visible_subtype: VisibleSubtype = VisibleSubtype.NONE
    confidence: AnnotationConfidence = AnnotationConfidence.MEDIUM
    created_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        self.requirement_id = _require_non_empty(self.requirement_id, "requirement_id")
        self.flow_id = _require_non_empty(self.flow_id, "flow_id")
        self.text = _require_non_empty(self.text, "text")
        self.source_gold_requirement_id = _require_non_empty(
            self.source_gold_requirement_id,
            "source_gold_requirement_id",
        )
        self.source_gold_text = _require_non_empty(self.source_gold_text, "source_gold_text")
        self.generation_rationale = _normalize_optional_text(self.generation_rationale)
        self.generation_model = _normalize_optional_text(self.generation_model)
        self.generation_prompt_path = _normalize_optional_text(self.generation_prompt_path)
        self.created_at = _require_non_empty(self.created_at, "created_at")

        if self.ui_evaluability == UiEvaluability.UI_VERIFIABLE:
            self.non_evaluable_reason = NonEvaluableReason.NONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "flow_id": self.flow_id,
            "text": self.text,
            "source_gold_requirement_id": self.source_gold_requirement_id,
            "source_gold_text": self.source_gold_text,
            "mutation_family": self.mutation_family.value,
            "intended_label": self.intended_label.value,
            "generation_rationale": self.generation_rationale,
            "review_status": self.review_status.value,
            "generation_model": self.generation_model,
            "generation_prompt_path": self.generation_prompt_path,
            "grounding_scope": self.grounding_scope.value,
            "requirement_type": self.requirement_type.value,
            "ui_evaluability": self.ui_evaluability.value,
            "non_evaluable_reason": self.non_evaluable_reason.value,
            "visible_subtype": self.visible_subtype.value,
            "confidence": self.confidence.value,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContrastiveCandidateRequirement":
        return cls(
            requirement_id=data["requirement_id"],
            flow_id=data["flow_id"],
            text=data["text"],
            source_gold_requirement_id=data["source_gold_requirement_id"],
            source_gold_text=data["source_gold_text"],
            mutation_family=MutationFamily(data["mutation_family"]),
            intended_label=IntendedLabel(data["intended_label"]),
            generation_rationale=data.get("generation_rationale"),
            review_status=RequirementReviewStatus(
                data.get("review_status", RequirementReviewStatus.CANDIDATE.value)
            ),
            generation_model=data.get("generation_model"),
            generation_prompt_path=data.get("generation_prompt_path"),
            grounding_scope=GroundingScope(
                data.get("grounding_scope", GroundingScope.INDIRECT_FLOW_GROUNDED.value)
            ),
            requirement_type=RequirementInspectionType(
                data.get("requirement_type", RequirementInspectionType.UNCLEAR.value)
            ),
            ui_evaluability=UiEvaluability(
                data.get("ui_evaluability", UiEvaluability.PARTIALLY_UI_VERIFIABLE.value)
            ),
            non_evaluable_reason=NonEvaluableReason(
                data.get("non_evaluable_reason", NonEvaluableReason.BUSINESS_RULE_NOT_VISIBLE.value)
            ),
            visible_subtype=VisibleSubtype(data.get("visible_subtype", VisibleSubtype.NONE.value)),
            confidence=AnnotationConfidence(data.get("confidence", AnnotationConfidence.MEDIUM.value)),
            created_at=data.get("created_at", _utc_now_iso()),
        )


@dataclass(slots=True)
class ContrastiveCandidateFile:
    dataset: str
    flow_id: str
    requirements: list[ContrastiveCandidateRequirement]
    flow_overview: str | None = None
    capability_summary: list[str] = field(default_factory=list)
    generation_model: str | None = None
    generation_temperature: float | None = None

    def __post_init__(self) -> None:
        self.dataset = _require_non_empty(self.dataset, "dataset")
        self.flow_id = _require_non_empty(self.flow_id, "flow_id")
        self.flow_overview = _normalize_optional_text(self.flow_overview)
        self.capability_summary = _normalize_summary(self.capability_summary)
        self.generation_model = _normalize_optional_text(self.generation_model)

        for req in self.requirements:
            if req.flow_id != self.flow_id:
                raise ValueError(
                    f"Contrastive requirement flow_id mismatch: {req.requirement_id} has flow_id={req.flow_id}, "
                    f"expected {self.flow_id}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "flow_id": self.flow_id,
            "flow_overview": self.flow_overview,
            "capability_summary": self.capability_summary,
            "generation_model": self.generation_model,
            "generation_temperature": self.generation_temperature,
            "requirements": [req.to_dict() for req in self.requirements],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContrastiveCandidateFile":
        return cls(
            dataset=data["dataset"],
            flow_id=data["flow_id"],
            flow_overview=data.get("flow_overview"),
            capability_summary=list(data.get("capability_summary", [])),
            generation_model=data.get("generation_model"),
            generation_temperature=data.get("generation_temperature"),
            requirements=[
                ContrastiveCandidateRequirement.from_dict(item)
                for item in data.get("requirements", [])
            ],
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ContrastiveCandidateFile":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)


def list_gold_flow_ids(gold_root: Path = DEFAULT_GOLD_ROOT) -> list[str]:
    return sorted(path.parent.name for path in gold_root.glob("*/gold_requirements.json"))


def load_gold_requirements(flow_id: str, gold_root: Path = DEFAULT_GOLD_ROOT) -> GoldRequirementFile:
    path = gold_root / flow_id / "gold_requirements.json"
    if not path.exists():
        raise FileNotFoundError(f"Gold requirements not found: {path}")
    gold_file = GoldRequirementFile.load(path)
    if not gold_file.requirements:
        raise ValueError(f"No gold requirements available for flow {flow_id}")
    return gold_file


def load_task_context(flow_id: str, flow_root: Path = DEFAULT_FLOW_ROOT) -> dict[str, Any]:
    path = flow_root / flow_id / "task.json"
    if not path.exists():
        raise FileNotFoundError(f"Task metadata not found: {path}")
    task = load_json(path)
    if not isinstance(task, dict):
        raise ValueError(f"Task metadata must be a JSON object: {path}")
    return task


def load_optional_flow_metadata(
    flow_id: str,
    context_root: Path = DEFAULT_CONTEXT_ROOT,
) -> tuple[str | None, list[str]]:
    for filename in ("harvested_requirements.json", "candidate_requirements.json"):
        path = context_root / flow_id / filename
        if not path.exists():
            continue
        try:
            data = load_json(path)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        flow_overview = _normalize_optional_text(data.get("flow_overview"))
        capability_summary = _normalize_summary(data.get("capability_summary"))
        if flow_overview or capability_summary:
            return flow_overview, capability_summary
    return None, []


def build_contrastive_source_payload(
    gold_file: GoldRequirementFile,
    *,
    flow_overview: str | None = None,
    capability_summary: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "flow_overview": flow_overview,
        "capability_summary": _normalize_summary(capability_summary),
        "accepted_gold_requirements": [
            {
                "requirement_id": requirement.requirement_id,
                "text": requirement.text,
                "scope": requirement.scope.value,
                "tags": list(requirement.tags),
                "step_indices": list(requirement.step_indices),
                "requirement_type": requirement.requirement_type.value,
                "ui_evaluability": requirement.ui_evaluability.value,
                "visible_subtype": requirement.visible_subtype.value,
                "manual_verification_label": requirement.manual_verification_label,
            }
            for requirement in gold_file.requirements
        ],
    }


def build_prompt_for_flow(
    flow_id: str,
    *,
    gold_root: Path = DEFAULT_GOLD_ROOT,
    flow_root: Path = DEFAULT_FLOW_ROOT,
    context_root: Path = DEFAULT_CONTEXT_ROOT,
    target_partially: int = 5,
    target_abstain: int = 5,
    target_not_fulfilled: int = 5,
) -> tuple[str, dict[str, Any], GoldRequirementFile, dict[str, Any]]:
    gold_file = load_gold_requirements(flow_id, gold_root=gold_root)
    task = load_task_context(flow_id, flow_root=flow_root)
    flow_overview, capability_summary = load_optional_flow_metadata(flow_id, context_root=context_root)
    source_payload = build_contrastive_source_payload(
        gold_file,
        flow_overview=flow_overview,
        capability_summary=capability_summary,
    )
    prompt = build_contrastive_from_gold_prompt(
        task=task,
        gold_payload=source_payload,
        target_partially=target_partially,
        target_abstain=target_abstain,
        target_not_fulfilled=target_not_fulfilled,
    )
    return prompt, task, gold_file, source_payload


def prepare_manual_bundle(
    *,
    output_dir: Path,
    prompt: str,
    task: dict[str, Any],
    gold_file: GoldRequirementFile,
    model_name: str,
    temperature: float,
    target_partially: int,
    target_abstain: int,
    target_not_fulfilled: int,
) -> Path:
    bundle_dir = output_dir / MANUAL_BUNDLE_DIRNAME
    bundle_dir.mkdir(parents=True, exist_ok=True)

    (bundle_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    (bundle_dir / "task.json").write_text(
        json.dumps(task, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (bundle_dir / "gold_requirements.json").write_text(
        json.dumps(gold_file.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (bundle_dir / "generation_context.json").write_text(
        json.dumps(
            {
                "flow_id": gold_file.flow_id,
                "model": model_name,
                "temperature": temperature,
                "target_partially": target_partially,
                "target_abstain": target_abstain,
                "target_not_fulfilled": target_not_fulfilled,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (bundle_dir / "README.md").write_text(
        """# Manual contrastive generation bundle

1. Open `prompt.txt`.
2. Run it manually in ChatGPT / Codex.
3. Paste the raw response into `manual_contrastive_raw.txt`.
4. Re-run the script with `--parse-existing-response`.
5. Final output will be saved as `contrastive_candidates.json`.
""",
        encoding="utf-8",
    )
    (bundle_dir / "manual_contrastive_raw.txt").touch(exist_ok=True)
    return bundle_dir


def normalize_model_contrastive_candidates(
    *,
    parsed: dict[str, Any],
    gold_file: GoldRequirementFile,
    model_name: str,
    prompt_path: Path,
    output_dir: Path,
    generation_temperature: float,
    source_flow_overview: str | None = None,
    source_capability_summary: list[str] | None = None,
) -> ContrastiveCandidateFile:
    raw_requirements = parsed.get("requirements", [])
    if not isinstance(raw_requirements, list):
        raise ValueError("Parsed model output must contain a list under 'requirements'.")

    gold_by_id = {requirement.requirement_id: requirement for requirement in gold_file.requirements}
    requirements: list[ContrastiveCandidateRequirement] = []

    for item in raw_requirements:
        if not isinstance(item, dict):
            continue

        source_gold_requirement_id = str(item.get("source_gold_requirement_id") or "").strip()
        if not source_gold_requirement_id or source_gold_requirement_id not in gold_by_id:
            continue

        source_gold = gold_by_id[source_gold_requirement_id]
        candidate_text = str(item.get("candidate_text") or item.get("text") or "").strip()
        if not candidate_text:
            continue

        if _texts_too_similar(candidate_text, source_gold.text, strict=False):
            continue

        if any(_texts_too_similar(candidate_text, existing.text, strict=True) for existing in requirements):
            continue

        intended_label = _parse_enum(item.get("intended_label"), IntendedLabel)
        mutation_family = _parse_enum(item.get("mutation_family"), MutationFamily)
        if intended_label is None or mutation_family is None:
            continue

        ui_evaluability = _coerce_enum(
            item.get("ui_evaluability"),
            UiEvaluability,
            UiEvaluability.PARTIALLY_UI_VERIFIABLE,
        )
        non_evaluable_reason = _coerce_enum(
            item.get("non_evaluable_reason"),
            NonEvaluableReason,
            _default_non_evaluable_reason(ui_evaluability),
        )
        if ui_evaluability == UiEvaluability.UI_VERIFIABLE:
            non_evaluable_reason = NonEvaluableReason.NONE

        visible_subtype = _coerce_enum(
            item.get("visible_subtype"),
            VisibleSubtype,
            source_gold.visible_subtype,
        )
        requirement_type = _coerce_enum(
            item.get("requirement_type"),
            RequirementInspectionType,
            source_gold.requirement_type,
        )
        grounding_scope = _coerce_enum(
            item.get("grounding_scope"),
            GroundingScope,
            GroundingScope.INDIRECT_FLOW_GROUNDED,
        )
        generation_rationale = str(item.get("generation_rationale") or "").strip() or None

        requirement = ContrastiveCandidateRequirement(
            requirement_id="TEMP",
            flow_id=gold_file.flow_id,
            text=candidate_text,
            source_gold_requirement_id=source_gold_requirement_id,
            source_gold_text=source_gold.text,
            mutation_family=mutation_family,
            intended_label=intended_label,
            generation_rationale=generation_rationale,
            review_status=RequirementReviewStatus.CANDIDATE,
            generation_model=model_name,
            generation_prompt_path=_relative_prompt_path(prompt_path, output_dir),
            grounding_scope=grounding_scope,
            requirement_type=requirement_type,
            ui_evaluability=ui_evaluability,
            non_evaluable_reason=non_evaluable_reason,
            visible_subtype=visible_subtype,
            confidence=parse_confidence_label(item.get("confidence")),
        )
        requirements.append(requirement)

    for idx, requirement in enumerate(requirements, start=1):
        requirement.requirement_id = f"CONTR-{idx:02d}"

    flow_overview = str(parsed.get("flow_overview") or source_flow_overview or "").strip() or None
    capability_summary = parsed.get("capability_summary", source_capability_summary or [])
    capability_summary = _normalize_summary(capability_summary)

    return ContrastiveCandidateFile(
        dataset=gold_file.dataset or DATASET_NAME,
        flow_id=gold_file.flow_id,
        flow_overview=flow_overview,
        capability_summary=capability_summary,
        generation_model=model_name,
        generation_temperature=generation_temperature,
        requirements=requirements,
    )


def default_raw_response_path(output_dir: Path) -> Path:
    return output_dir / MANUAL_BUNDLE_DIRNAME / "manual_contrastive_raw.txt"


def parse_existing_response(
    *,
    flow_id: str,
    raw_response_path: Path,
    model_name: str,
    generation_temperature: float,
    gold_root: Path = DEFAULT_GOLD_ROOT,
    flow_root: Path = DEFAULT_FLOW_ROOT,
    context_root: Path = DEFAULT_CONTEXT_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> ContrastiveCandidateFile:
    prompt, _, gold_file, source_payload = build_prompt_for_flow(
        flow_id,
        gold_root=gold_root,
        flow_root=flow_root,
        context_root=context_root,
    )
    output_dir = output_root / flow_id
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle_dir = output_dir / MANUAL_BUNDLE_DIRNAME
    prompt_path = bundle_dir / "prompt.txt"
    if not prompt_path.exists():
        bundle_dir.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")

    if not raw_response_path.exists():
        raise FileNotFoundError(f"Raw response file not found: {raw_response_path}")

    raw_text = raw_response_path.read_text(encoding="utf-8")
    parsed = parse_json_response(raw_text)
    (raw_response_path.parent / "manual_contrastive_parsed.json").write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    contrastive_file = normalize_model_contrastive_candidates(
        parsed=parsed,
        gold_file=gold_file,
        model_name=model_name,
        prompt_path=prompt_path,
        output_dir=output_dir,
        generation_temperature=generation_temperature,
        source_flow_overview=source_payload.get("flow_overview"),
        source_capability_summary=list(source_payload.get("capability_summary", [])),
    )
    contrastive_file.save(output_dir / "contrastive_candidates.json")
    return contrastive_file


def prepare_bundle_for_flow(
    *,
    flow_id: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    gold_root: Path = DEFAULT_GOLD_ROOT,
    flow_root: Path = DEFAULT_FLOW_ROOT,
    context_root: Path = DEFAULT_CONTEXT_ROOT,
    target_partially: int = 5,
    target_abstain: int = 5,
    target_not_fulfilled: int = 5,
    model_name: str = "manual-chatgpt",
    temperature: float = 0.2,
) -> tuple[Path, str]:
    prompt, task, gold_file, _ = build_prompt_for_flow(
        flow_id,
        gold_root=gold_root,
        flow_root=flow_root,
        context_root=context_root,
        target_partially=target_partially,
        target_abstain=target_abstain,
        target_not_fulfilled=target_not_fulfilled,
    )
    output_dir = output_root / flow_id
    bundle_dir = prepare_manual_bundle(
        output_dir=output_dir,
        prompt=prompt,
        task=task,
        gold_file=gold_file,
        model_name=model_name,
        temperature=temperature,
        target_partially=target_partially,
        target_abstain=target_abstain,
        target_not_fulfilled=target_not_fulfilled,
    )
    return bundle_dir, prompt


def maybe_print_or_copy_prompt(*, prompt: str, print_prompt: bool, copy_prompt: bool, flow_id: str) -> None:
    if print_prompt:
        print("\n===== CONTRASTIVE PROMPT START =====\n")
        print(prompt)
        print("\n===== CONTRASTIVE PROMPT END =====\n")

    if copy_prompt:
        if _copy_prompt_to_clipboard(prompt):
            print(f"[OK] Copied prompt to clipboard for {flow_id}")
        else:
            print(f"[WARN] Could not copy prompt to clipboard for {flow_id}")
