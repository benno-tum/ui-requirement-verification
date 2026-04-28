from __future__ import annotations

from pathlib import Path

from ui_verifier.verification.schemas import VerificationRun


BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_ROOT = BASE_DIR / "data" / "generated" / "verification_runs"


class VerificationStorage:
    def __init__(self, output_root: Path | None = None) -> None:
        self.output_root = output_root or DEFAULT_OUTPUT_ROOT

    def run_dir(self, flow_id: str) -> Path:
        return self.output_root / flow_id

    def run_file_path(self, flow_id: str) -> Path:
        return self.run_dir(flow_id) / "verification_run.json"

    def save_run(self, run: VerificationRun) -> Path:
        path = self.run_file_path(run.flow_id)
        run.save(path)
        return path

    def load_run(self, flow_id: str) -> VerificationRun:
        path = self.run_file_path(flow_id)
        if not path.exists():
            raise FileNotFoundError(f"Verification run not found: {path}")
        return VerificationRun.load(path)
