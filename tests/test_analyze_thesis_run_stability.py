from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPT_DIR = BASE_DIR / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT_PATH = SCRIPT_DIR / "analyze_thesis_run_stability.py"
SPEC = importlib.util.spec_from_file_location("analyze_thesis_run_stability", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_descriptive_reports_sample_statistics() -> None:
    result = MODULE._descriptive([0.7, 0.8, 0.9])
    assert result["mean"] == 0.8
    assert round(result["sample_standard_deviation"], 6) == 0.1
    assert result["minimum"] == 0.7
    assert result["maximum"] == 0.9


def test_default_families_have_original_plus_two_repetitions() -> None:
    assert set(MODULE.DEFAULT_FAMILIES) == {
        "fl_raw_all",
        "fl_gated_top4",
        "qwen_raw_top4",
    }
    assert all(len(run_ids) == 3 for run_ids in MODULE.DEFAULT_FAMILIES.values())
