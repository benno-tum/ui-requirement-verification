from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts/run_smolvlm_open_baseline.py"
SPEC = importlib.util.spec_from_file_location("run_smolvlm_open_baseline", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_parse_predictions_filters_unattached_steps() -> None:
    parsed = MODULE._parse_predictions(
        """
        ```json
        {"claims":[{"claim_id":"REQ-1-C1","ui_evaluability":"UI_VERIFIABLE",
        "claim_status":"SUPPORTED","evidence_step_indices":[2,9],"rationale":"visible"}]}
        ```
        """,
        [1, 2, 3],
    )

    assert parsed["REQ-1-C1"]["status"] == "SUPPORTED"
    assert parsed["REQ-1-C1"]["evidence_steps"] == [2]


def test_final_label_is_conservative_without_evidence() -> None:
    assert MODULE._final_label("SUPPORTED", "UI_VERIFIABLE", []) == "ABSTAIN"
    assert MODULE._final_label("CONTRADICTED", "UI_VERIFIABLE", []) == "NOT_FULFILLED"
    assert MODULE._final_label("PARTIALLY_SUPPORTED", "UI_VERIFIABLE", [4]) == "PARTIALLY_FULFILLED"
