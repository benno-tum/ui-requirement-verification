from __future__ import annotations

import json
from pathlib import Path

from ui_verifier.evaluation.prediction_coverage import coverage_for_files


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_prediction_coverage_reports_missing_contrastive_ids(tmp_path: Path) -> None:
    gold_path = tmp_path / "verification_gold.json"
    prediction_path = tmp_path / "prediction.json"
    _write_json(
        gold_path,
        {
            "items": [
                {"requirement_id": "REQ-01", "text": "Visible search."},
                {"requirement_id": "CONTR-01", "text": "Preserve search state."},
                {"requirement_id": "CONTR-02", "text": "Reject invalid state."},
            ]
        },
    )
    _write_json(
        prediction_path,
        {
            "results": [
                {"requirement_id": "REQ-01", "final_label": "FULFILLED"},
                {"requirement_id": "REQ-EXTRA", "final_label": "ABSTAIN"},
            ]
        },
    )

    coverage = coverage_for_files(gold_path, prediction_path).to_dict()

    assert coverage["total_reviewed"] == 3
    assert coverage["total_predictions"] == 2
    assert coverage["missing_prediction_ids"] == ["CONTR-01", "CONTR-02"]
    assert coverage["missing_by_prefix"] == {"CONTR": 2}
    assert coverage["extra_prediction_ids"] == ["REQ-EXTRA"]


def test_prediction_coverage_is_complete_for_selected_benchmark_ids(tmp_path: Path) -> None:
    gold_path = tmp_path / "verification_gold.json"
    prediction_path = tmp_path / "prediction.json"
    _write_json(
        gold_path,
        {
            "items": [
                {"requirement_id": "REQ-01", "text": "Visible search."},
                {"requirement_id": "CONTR-01", "text": "Preserve search state."},
            ]
        },
    )
    _write_json(
        prediction_path,
        {
            "results": [
                {"requirement_id": "REQ-01", "final_label": "FULFILLED"},
                {"requirement_id": "CONTR-01", "final_label": "ABSTAIN"},
            ]
        },
    )

    coverage = coverage_for_files(gold_path, prediction_path).to_dict()

    assert coverage["prediction_coverage"] == 1.0
    assert coverage["missing_prediction_count"] == 0
