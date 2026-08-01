from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BASE_DIR / "scripts/audit_thesis_replication_package.py"
SPEC = importlib.util.spec_from_file_location("audit_thesis_replication_package", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_clean_package_passes_and_hashes_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Sanitized aggregate metrics.", encoding="utf-8")

    result = MODULE.audit(tmp_path, manifest_name="artifact_manifest.json")

    assert result["release_gate_passed"] is True
    assert result["findings"] == []
    assert len(result["files"]) == 1


def test_absolute_path_and_secret_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text(
        '{\"path\":\"/Users/example/private/file\", \"api_key\":\"sk-example-secret\"}',
        encoding="utf-8",
    )

    result = MODULE.audit(tmp_path, manifest_name="artifact_manifest.json")

    assert result["release_gate_passed"] is False
    assert {item["kind"] for item in result["findings"]} == {
        "absolute_personal_path",
        "possible_secret_assignment",
    }
