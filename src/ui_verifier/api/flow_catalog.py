from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ui_verifier.annotation.storage import AnnotationStorage
from ui_verifier.common.flow_utils import find_flow_dirs, find_step_images, parse_step_number
from ui_verifier.verification.storage import VerificationStorage


BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_FLOWS_ROOT = BASE_DIR / "data" / "processed" / "flows"


class FlowCatalog:
    def __init__(
        self,
        flows_root: Path | None = None,
        annotation_storage: AnnotationStorage | None = None,
        verification_storage: VerificationStorage | None = None,
    ) -> None:
        self.flows_root = flows_root or DEFAULT_FLOWS_ROOT
        self.annotation_storage = annotation_storage or AnnotationStorage()
        self.verification_storage = verification_storage or VerificationStorage()

    def list_flows(self) -> list[dict[str, Any]]:
        flows: list[dict[str, Any]] = []
        if not self.flows_root.exists():
            return flows

        for dataset_dir in sorted(p for p in self.flows_root.iterdir() if p.is_dir()):
            for flow_dir in find_flow_dirs(dataset_dir):
                flows.append(self._build_flow_summary(dataset_dir.name, flow_dir))
        return flows

    def get_flow(self, flow_id: str) -> dict[str, Any]:
        dataset, flow_dir = self.resolve_flow(flow_id)
        return self._build_flow_summary(dataset, flow_dir, include_task=True)

    def get_flow_steps(self, flow_id: str) -> list[dict[str, Any]]:
        dataset, flow_dir = self.resolve_flow(flow_id)
        steps: list[dict[str, Any]] = []
        for step_path in find_step_images(flow_dir):
            step_index = parse_step_number(step_path)
            steps.append(
                {
                    "dataset": dataset,
                    "flow_id": flow_id,
                    "step_index": step_index,
                    "image_name": step_path.name,
                    "image_url": self.image_url(dataset, flow_id, step_path.name),
                }
            )
        return steps

    def resolve_flow(self, flow_id: str) -> tuple[str, Path]:
        matches: list[tuple[str, Path]] = []
        if not self.flows_root.exists():
            raise FileNotFoundError(f"Flows root not found: {self.flows_root}")

        for dataset_dir in sorted(p for p in self.flows_root.iterdir() if p.is_dir()):
            candidate = dataset_dir / flow_id
            if candidate.is_dir():
                matches.append((dataset_dir.name, candidate))

        if not matches:
            raise FileNotFoundError(f"Flow not found: {flow_id}")
        if len(matches) > 1:
            datasets = ", ".join(dataset for dataset, _ in matches)
            raise ValueError(f"Flow id is ambiguous across datasets: {flow_id} ({datasets})")
        return matches[0]

    @staticmethod
    def image_url(dataset: str, flow_id: str, image_name: str) -> str:
        return f"/static/flows/{dataset}/{flow_id}/{image_name}"

    def _build_flow_summary(
        self,
        dataset: str,
        flow_dir: Path,
        *,
        include_task: bool = False,
    ) -> dict[str, Any]:
        flow_id = flow_dir.name
        step_paths = find_step_images(flow_dir)
        task = self._load_json(flow_dir / "task.json")
        candidate_count = self._safe_candidate_count(flow_id)
        gold_count = self._safe_gold_count(flow_id)
        has_verification_run = self._has_verification_run(flow_id)

        summary: dict[str, Any] = {
            "dataset": dataset,
            "flow_id": flow_id,
            "flow_dir": str(flow_dir),
            "num_steps": len(step_paths),
            "step_indices": [parse_step_number(path) for path in step_paths],
            "website": task.get("website") if isinstance(task, dict) else None,
            "domain": task.get("domain") if isinstance(task, dict) else None,
            "confirmed_task": task.get("confirmed_task") if isinstance(task, dict) else None,
            "candidate_count": candidate_count,
            "gold_count": gold_count,
            "has_verification_run": has_verification_run,
        }

        if include_task:
            summary["task"] = task
        return summary

    def _safe_candidate_count(self, flow_id: str) -> int:
        try:
            return len(self.annotation_storage.load_candidate_file(flow_id).requirements)
        except FileNotFoundError:
            return 0

    def _safe_gold_count(self, flow_id: str) -> int:
        gold_file = self.annotation_storage.load_gold_file(flow_id)
        return 0 if gold_file is None else len(gold_file.requirements)

    def _has_verification_run(self, flow_id: str) -> bool:
        return self.verification_storage.run_file_path(flow_id).exists()

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any] | list[Any] | None:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
