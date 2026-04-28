from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image

from ui_verifier.annotation.storage import AnnotationStorage
from ui_verifier.common.flow_utils import find_flow_dirs, find_step_images, parse_step_number
from ui_verifier.data.mind2web_originals import ensure_flow_original_images
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
        self._original_download_attempted: set[str] = set()

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
        self._maybe_backfill_original_step_images(dataset, flow_id, flow_dir)
        steps: list[dict[str, Any]] = []
        for step_path in find_step_images(flow_dir):
            step_index = parse_step_number(step_path)
            preview_meta = self._read_image_meta(step_path)
            preferred_path = self._preferred_step_image_path(flow_dir, flow_id, step_path)
            preferred_meta = self._read_image_meta(preferred_path)
            steps.append(
                {
                    "dataset": dataset,
                    "flow_id": flow_id,
                    "step_index": step_index,
                    "image_name": step_path.name,
                    "image_url": self._url_for_step_asset(dataset, flow_id, preferred_path),
                    "preview_image_url": self.image_url(dataset, flow_id, step_path.relative_to(flow_dir).as_posix()),
                    "original_image_url": self._url_for_step_asset(dataset, flow_id, preferred_path) if preferred_path != step_path else None,
                    "image_width": preferred_meta[0],
                    "image_height": preferred_meta[1],
                    "preview_image_width": preview_meta[0],
                    "preview_image_height": preview_meta[1],
                }
            )
        return steps


    def _maybe_backfill_original_step_images(self, dataset: str, flow_id: str, flow_dir: Path) -> None:
        if dataset != "mind2web":
            return
        if flow_id in self._original_download_attempted:
            return
        self._original_download_attempted.add(flow_id)
        try:
            ensure_flow_original_images(flow_dir)
        except Exception:
            return

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

    @staticmethod
    def candidate_asset_url(flow_id: str, asset_path: str) -> str:
        return f"/static/candidate_artifacts/{flow_id}/{asset_path}"

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
        pending_candidate_count = self._safe_candidate_count(flow_id, only_pending=True)
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
            "pending_candidate_count": pending_candidate_count,
            "gold_count": gold_count,
            "has_verification_run": has_verification_run,
        }

        if include_task:
            summary["task"] = task
        return summary

    def _safe_candidate_count(self, flow_id: str, only_pending: bool = False) -> int:
        try:
            requirements = self.annotation_storage.load_candidate_file(flow_id).requirements
        except FileNotFoundError:
            return 0

        if not only_pending:
            return len(requirements)

        pending_statuses = {"candidate", "needs_review"}
        return sum(1 for requirement in requirements if getattr(requirement.review_status, "value", requirement.review_status) in pending_statuses)

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


    def _preferred_step_image_path(self, flow_dir: Path, flow_id: str, step_path: Path) -> Path:
        base_meta = self._read_image_meta(step_path)
        if base_meta == (0, 0):
            return step_path

        for candidate in self._candidate_step_image_paths(flow_dir, flow_id, step_path):
            if not candidate.exists() or candidate == step_path:
                continue
            candidate_meta = self._read_image_meta(candidate)
            if self._is_better_image(candidate_meta, base_meta, candidate, step_path):
                return candidate
        return step_path

    def _candidate_step_image_paths(self, flow_dir: Path, flow_id: str, step_path: Path) -> list[Path]:
        stem = step_path.stem
        suffix = step_path.suffix
        return [
            flow_dir / "original" / step_path.name,
            flow_dir / "originals" / step_path.name,
            flow_dir / "full" / step_path.name,
            flow_dir / "fullres" / step_path.name,
            flow_dir / "hires" / step_path.name,
            flow_dir / "sharp" / step_path.name,
            flow_dir / f"{stem}.original{suffix}",
            flow_dir / f"{stem}_original{suffix}",
            flow_dir / f"{stem}.full{suffix}",
            flow_dir / f"{stem}_full{suffix}",
            flow_dir / f"{stem}.hires{suffix}",
            flow_dir / f"{stem}_hires{suffix}",
            self.annotation_storage.candidate_dir(flow_id) / "manual_harvest_bundle" / "images" / step_path.name,
        ]

    @staticmethod
    def _read_image_meta(path: Path) -> tuple[int, int]:
        try:
            with Image.open(path) as image:
                return int(image.width), int(image.height)
        except Exception:
            return 0, 0

    @staticmethod
    def _is_better_image(candidate_meta: tuple[int, int], base_meta: tuple[int, int], candidate_path: Path, base_path: Path) -> bool:
        candidate_width, candidate_height = candidate_meta
        base_width, base_height = base_meta
        if candidate_width <= 0 or candidate_height <= 0:
            return False
        if candidate_width * candidate_height > base_width * base_height:
            return True
        if candidate_width >= base_width and candidate_height >= base_height:
            try:
                return candidate_path.stat().st_size > base_path.stat().st_size * 1.1
            except OSError:
                return False
        return False

    def _url_for_step_asset(self, dataset: str, flow_id: str, asset_path: Path) -> str:
        try:
            relative_to_flow = asset_path.relative_to(self.flows_root / dataset / flow_id)
            return self.image_url(dataset, flow_id, relative_to_flow.as_posix())
        except ValueError:
            relative_to_candidate_dir = asset_path.relative_to(self.annotation_storage.candidate_dir(flow_id))
            return self.candidate_asset_url(flow_id, relative_to_candidate_dir.as_posix())
