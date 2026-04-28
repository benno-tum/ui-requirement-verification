from __future__ import annotations

from pathlib import Path

from ui_verifier.requirements.schemas import (
    CandidateRequirementFile,
    GoldRequirementFile,
    HarvestedRequirementFile,
)


BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_GENERATED_CANDIDATE_ROOT = BASE_DIR / "data" / "generated" / "candidate_requirements"
DEFAULT_VERSIONED_CANDIDATE_ROOT = BASE_DIR / "data" / "annotations" / "requirements_candidate"
DEFAULT_GOLD_ROOT = BASE_DIR / "data" / "annotations" / "requirements_gold"


class AnnotationStorage:
    def __init__(
        self,
        candidate_root: Path | None = None,
        versioned_candidate_root: Path | None = None,
        gold_root: Path | None = None,
    ) -> None:
        # Generated artifacts stay local. Reviewed candidate requirement snapshots are versioned separately.
        self.candidate_root = candidate_root or DEFAULT_GENERATED_CANDIDATE_ROOT
        self.versioned_candidate_root = versioned_candidate_root or DEFAULT_VERSIONED_CANDIDATE_ROOT
        self.gold_root = gold_root or DEFAULT_GOLD_ROOT

    def generated_candidate_dir(self, flow_id: str) -> Path:
        return self.candidate_root / flow_id

    def versioned_candidate_dir(self, flow_id: str) -> Path:
        return self.versioned_candidate_root / flow_id

    def candidate_dir(self, flow_id: str) -> Path:
        versioned_dir = self.versioned_candidate_dir(flow_id)
        if versioned_dir.exists():
            return versioned_dir
        return self.generated_candidate_dir(flow_id)

    def harvested_file_path(self, flow_id: str) -> Path:
        return self.generated_candidate_dir(flow_id) / "harvested_requirements.json"

    def candidate_file_path(self, flow_id: str) -> Path:
        versioned_path = self.versioned_candidate_dir(flow_id) / "candidate_requirements.json"
        if versioned_path.exists():
            return versioned_path
        return self.generated_candidate_dir(flow_id) / "candidate_requirements.json"

    def writable_candidate_file_path(self, flow_id: str) -> Path:
        return self.versioned_candidate_dir(flow_id) / "candidate_requirements.json"

    def gold_dir(self, flow_id: str) -> Path:
        return self.gold_root / flow_id

    def gold_file_path(self, flow_id: str) -> Path:
        return self.gold_dir(flow_id) / "gold_requirements.json"

    def load_harvested_file(self, flow_id: str) -> HarvestedRequirementFile:
        path = self.harvested_file_path(flow_id)
        if not path.exists():
            raise FileNotFoundError(f"Harvested requirements not found: {path}")
        return HarvestedRequirementFile.load(path)

    def save_harvested_file(self, harvested_file: HarvestedRequirementFile) -> Path:
        path = self.harvested_file_path(harvested_file.flow_id)
        harvested_file.save(path)
        return path

    def load_candidate_file(self, flow_id: str) -> CandidateRequirementFile:
        path = self.candidate_file_path(flow_id)
        if not path.exists():
            raise FileNotFoundError(f"Candidate requirements not found: {path}")
        return CandidateRequirementFile.load(path)

    def save_candidate_file(self, candidate_file: CandidateRequirementFile) -> Path:
        path = self.writable_candidate_file_path(candidate_file.flow_id)
        candidate_file.save(path)
        return path

    def load_gold_file(self, flow_id: str) -> GoldRequirementFile | None:
        path = self.gold_file_path(flow_id)
        if not path.exists():
            return None
        return GoldRequirementFile.load(path)

    def save_gold_file(self, gold_file: GoldRequirementFile) -> Path:
        path = self.gold_file_path(gold_file.flow_id)
        gold_file.save(path)
        return path
