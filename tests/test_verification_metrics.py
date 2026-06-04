from __future__ import annotations

import json
from pathlib import Path

from ui_verifier.evaluation.verification_metrics import evaluate_predictions


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_evaluate_pipeline_output_metrics(tmp_path: Path) -> None:
    gold_root = tmp_path / "gold"
    flow_id = "flow_a"
    _write_json(
        gold_root / flow_id / "verification_gold.json",
        {
            "dataset": "mind2web",
            "flow_id": flow_id,
            "items": [
                {
                    "requirement_id": "REQ-1",
                    "flow_id": flow_id,
                    "text": "The system shows checkout.",
                    "verification_label": "FULFILLED",
                    "evidence_steps": [2, 3],
                    "claims": [
                        {
                            "claim": "The checkout summary is visible.",
                            "status": "SUPPORTED",
                            "evidence_steps": [2],
                        }
                    ],
                },
                {
                    "requirement_id": "REQ-2",
                    "flow_id": flow_id,
                    "text": "The system stores payment.",
                    "verification_label": "ABSTAIN",
                    "evidence_steps": [],
                    "claims": [
                        {
                            "claim": "The backend stores payment data.",
                            "status": "HIDDEN",
                            "evidence_steps": [],
                        }
                    ],
                },
            ],
        },
    )
    prediction_path = tmp_path / "predictions" / f"{flow_id}.json"
    _write_json(
        prediction_path,
        {
            "flow_id": flow_id,
            "results": [
                {
                    "requirement_id": "REQ-1",
                    "final_label": "FULFILLED",
                    "evidence": [
                        {"step_index": 1, "screenshot_path": "step_01.png", "visible_observation": "x"},
                        {"step_index": 2, "screenshot_path": "step_02.png", "visible_observation": "x"},
                    ],
                    "claims": [
                        {
                            "claim_text": "The checkout summary is visible to the user.",
                            "status": "SUPPORTED",
                            "evidence": [{"step_index": 2}],
                        }
                    ],
                },
                {
                    "requirement_id": "REQ-2",
                    "final_label": "FULFILLED",
                    "evidence": [{"step_index": 4, "screenshot_path": "step_04.png", "visible_observation": "x"}],
                    "claims": [
                        {
                            "claim_text": "The backend stores payment data.",
                            "status": "SUPPORTED",
                            "evidence": [{"step_index": 4}],
                        }
                    ],
                },
            ],
        },
    )

    metrics = evaluate_predictions(gold_root, prediction_path, k_values=[1, 2])

    assert metrics["gold_count"] == 2
    assert metrics["prediction_count"] == 2
    assert metrics["label_metrics"]["accuracy"] == 0.5
    assert metrics["label_metrics"]["false_fulfillment_rate"] == 0.5
    assert metrics["label_metrics"]["confusion_matrix"]["ABSTAIN"]["FULFILLED"] == 1
    assert metrics["evidence_metrics"]["recall_at_1"] == 0.0
    assert metrics["evidence_metrics"]["recall_at_2"] == 0.5
    assert metrics["evidence_metrics"]["mrr"] == 0.5
    assert metrics["claim_status_metrics"]["gold_claim_count"] == 2
    assert metrics["claim_status_metrics"]["matched_claims"] == 2
    assert metrics["claim_status_metrics"]["confusion_matrix"]["HIDDEN"]["SUPPORTED"] == 1


def test_missing_predictions_count_as_abstain(tmp_path: Path) -> None:
    gold_root = tmp_path / "gold"
    flow_id = "flow_b"
    _write_json(
        gold_root / flow_id / "verification_gold.json",
        {
            "flow_id": flow_id,
            "items": [
                {"requirement_id": "REQ-1", "flow_id": flow_id, "text": "x", "verification_label": "ABSTAIN"},
                {"requirement_id": "REQ-2", "flow_id": flow_id, "text": "y", "verification_label": "FULFILLED"},
            ],
        },
    )
    prediction_path = tmp_path / "verification_run.json"
    _write_json(
        prediction_path,
        {
            "flow_id": flow_id,
            "verdicts": [
                {"requirement_id": "REQ-1", "label": "ABSTAIN", "evidence": []},
            ],
        },
    )

    metrics = evaluate_predictions(gold_root, prediction_path)

    assert metrics["label_metrics"]["missing_predictions"] == 1
    assert metrics["label_metrics"]["prediction_coverage"] == 0.5
    assert metrics["label_metrics"]["confusion_matrix"]["FULFILLED"]["ABSTAIN"] == 1
