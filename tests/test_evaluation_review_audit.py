from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from ui_verifier.api import app as api_app
from ui_verifier.evaluation.review_audit import (
    EvaluationAuditStore,
    bbox_metrics,
    center_inside,
    classification_metrics,
    image_asset_metadata_errors,
    iou,
    validate_bbox_review,
    validate_ui_review,
    write_json,
)


def _audit_files(root: Path) -> Path:
    audit_dir = root / "audit-1"
    write_json(
        audit_dir / "audit.json",
        {
            "audit_id": "audit-1",
            "title": "Test audit",
            "created_at": "2026-07-17T00:00:00Z",
            "seed": 1,
            "ui_item_count": 1,
            "bbox_item_count": 1,
            "blind_review": True,
            "status": "ready_for_review",
        },
    )
    write_json(
        audit_dir / "ui_manifest.json",
        {
            "schema_version": "ui_evaluability_review_v1",
            "blind": True,
            "seed": 1,
            "sample_size": 1,
            "sampling_note": "test",
            "items": [
                {
                    "audit_item_id": "UI-001",
                    "flow_id": "flow-1",
                    "dataset": "mind2web",
                    "requirement_id": "REQ-1",
                    "requirement_text": "The page shall show search.",
                    "step_indices": [1],
                }
            ],
        },
    )
    write_json(
        audit_dir / "ui_reference.json",
        {
            "schema_version": "ui_evaluability_review_reference_v1",
            "items": {"UI-001": {"gold_label": "PARTIALLY_UI_VERIFIABLE"}},
        },
    )
    write_json(
        audit_dir / "bbox_manifest.json",
        {
            "schema_version": "bounding_box_review_v1",
            "blind": True,
            "seed": 1,
            "sample_size": 1,
            "sampling_note": "test",
            "items": [
                {
                    "audit_item_id": "BBOX-001",
                    "dataset": "mind2web",
                    "flow_id": "flow-1",
                    "requirement_id": "REQ-1",
                    "requirement_text": "The page shall show search.",
                    "claim_id": "REQ-1-C1",
                    "claim_text": "The page shows search.",
                    "step_index": 1,
                    "image_url": "/static/flows/mind2web/flow-1/step_01.png",
                    "image_path": "step_01.png",
                    "image_width": 100,
                    "image_height": 80,
                    "image_sha256": "a" * 64,
                    "coordinate_space": "image_pixels",
                }
            ],
        },
    )
    write_json(
        audit_dir / "bbox_reference.json",
        {
            "schema_version": "bounding_box_review_reference_v1",
            "items": {
                "BBOX-001": {
                    "prediction": {
                        "bbox": {"x1": 10, "y1": 10, "x2": 30, "y2": 30},
                        "matched_text": "search",
                        "score": 0.8,
                        "source": "tesseract",
                        "level": "word",
                    }
                }
            },
        },
    )
    return audit_dir


def test_ui_review_validation_and_classification_metrics() -> None:
    validated = validate_ui_review(
        {"label": "UI_VERIFIABLE", "rationale": "Visible control.", "confidence": 0.8, "ambiguous": False}
    )
    assert validated["label"] == "UI_VERIFIABLE"
    with pytest.raises(ValueError):
        validate_ui_review({"label": "UNKNOWN", "confidence": 0.5})

    metrics = classification_metrics(
        [
            ("NOT_UI_VERIFIABLE", "NOT_UI_VERIFIABLE"),
            ("PARTIALLY_UI_VERIFIABLE", "UI_VERIFIABLE"),
            ("UI_VERIFIABLE", "UI_VERIFIABLE"),
        ]
    )
    assert metrics["n"] == 3
    assert metrics["accuracy"] == pytest.approx(2 / 3)
    assert metrics["per_class"]["PARTIALLY_UI_VERIFIABLE"]["recall"] == 0
    assert -1 <= metrics["cohen_kappa"] <= 1
    assert -1 <= metrics["linear_weighted_kappa"] <= 1
    empty_class_metrics = classification_metrics([("UI_VERIFIABLE", "UI_VERIFIABLE")])
    assert empty_class_metrics["balanced_accuracy"] == 1
    assert empty_class_metrics["per_class"]["NOT_UI_VERIFIABLE"]["support"] == 0


def test_bbox_geometry_validation_and_metrics() -> None:
    gold = {"x1": 10.0, "y1": 10.0, "x2": 30.0, "y2": 30.0}
    prediction = {"x1": 15.0, "y1": 15.0, "x2": 25.0, "y2": 25.0}
    assert iou(gold, prediction) == pytest.approx(0.25)
    assert center_inside(prediction, gold)

    review = validate_bbox_review(
        {
            "applicability": "SINGLE_REGION",
            "gold_boxes": [gold],
            "evidence_note": "Search control.",
            "gold_locked": True,
            "relevance": "YES",
            "sufficiency": "YES",
            "error_categories": [],
        },
        image_width=100,
        image_height=80,
    )
    assert review["gold_locked"]
    with pytest.raises(ValueError):
        validate_bbox_review(
            {"applicability": "SINGLE_REGION", "gold_boxes": [{"x1": 0, "y1": 0, "x2": 110, "y2": 10}]},
            image_width=100,
            image_height=80,
        )

    metrics = bbox_metrics(
        [{"audit_item_id": "BBOX-001", "dataset": "mind2web", "image_width": 100, "image_height": 80}],
        {"BBOX-001": {"prediction": {"bbox": prediction}}},
        {"BBOX-001": review},
    )
    assert metrics["overall"]["coordinate_validity_rate"] == 1
    assert metrics["overall"]["proposal_coverage"] == 1
    assert metrics["overall"]["mean_maximum_iou"] == pytest.approx(0.25)
    assert metrics["overall"]["center_inside_gold_rate"] == 1

    multi = validate_bbox_review(
        {
            "applicability": "MULTI_REGION",
            "gold_boxes": [gold, {"x1": 40, "y1": 10, "x2": 60, "y2": 30}],
        },
        image_width=100,
        image_height=80,
    )
    assert len(multi["gold_boxes"]) == 2
    null_metrics = bbox_metrics(
        [{"audit_item_id": "BBOX-002", "dataset": "pure", "image_width": 100, "image_height": 80}],
        {"BBOX-002": {"prediction": None}},
        {"BBOX-002": {**multi, "gold_locked": True}},
    )
    assert null_metrics["overall"]["proposal_coverage"] == 0
    assert null_metrics["overall"]["coordinate_validity_rate"] is None


def test_image_asset_metadata_dimensions_hash_and_coordinate_space(tmp_path: Path) -> None:
    image_path = tmp_path / "step.png"
    Image.new("RGB", (100, 80), "white").save(image_path)
    from ui_verifier.evaluation.review_audit import sha256_file

    item = {
        "image_path": str(image_path),
        "image_width": 100,
        "image_height": 80,
        "image_sha256": sha256_file(image_path),
        "coordinate_space": "image_pixels",
    }
    assert image_asset_metadata_errors(item) == []
    assert image_asset_metadata_errors({**item, "image_width": 99}) == ["IMAGE_DIMENSION_MISMATCH"]
    assert image_asset_metadata_errors({**item, "image_sha256": "0" * 64}) == ["IMAGE_HASH_MISMATCH"]


def test_store_hides_private_references_until_gold_is_locked(tmp_path: Path) -> None:
    root = tmp_path / "audits"
    _audit_files(root)
    store = EvaluationAuditStore(root)

    initial = store.public_items_for_reviewer("audit-1", "reviewer", "bbox")
    assert "prediction" not in initial["items"][0]
    assert "gold_label" not in store.public_items_for_reviewer("audit-1", "reviewer", "ui")["items"][0]

    store.save_review(
        "audit-1",
        "reviewer",
        "bbox",
        "BBOX-001",
        {
            "applicability": "SINGLE_REGION",
            "gold_boxes": [{"x1": 10, "y1": 10, "x2": 30, "y2": 30}],
            "evidence_note": "reference",
            "gold_locked": True,
            "relevance": "NOT_APPLICABLE",
            "sufficiency": "NOT_APPLICABLE",
            "error_categories": [],
        },
    )
    revealed = store.public_items_for_reviewer("audit-1", "reviewer", "bbox")
    assert revealed["items"][0]["prediction"]["matched_text"] == "search"


def test_audit_api_blind_review_and_locked_reference(tmp_path: Path, monkeypatch) -> None:
    audit_root = tmp_path / "audits"
    _audit_files(audit_root)
    monkeypatch.setattr(api_app, "EVALUATION_AUDIT_ROOT", audit_root)

    public_ui = api_app.get_ui_evaluability_audit_items("audit-1", "colleague")
    assert "gold_label" not in json.dumps(public_ui)
    ui_response = api_app.save_ui_evaluability_audit_review(
        "audit-1",
        "UI-001",
        api_app.UiEvaluabilityAuditReviewRequest(
            reviewer_id="colleague",
            label="PARTIALLY_UI_VERIFIABLE",
            rationale="Visible core plus hidden behavior.",
            confidence=0.9,
        ),
    )
    assert ui_response["review"]["label"] == "PARTIALLY_UI_VERIFIABLE"

    bbox_response = api_app.save_bounding_box_audit_review(
        "audit-1",
        "BBOX-001",
        api_app.BoundingBoxAuditReviewRequest(
            reviewer_id="colleague",
            applicability="SINGLE_REGION",
            gold_boxes=[{"x1": 10, "y1": 10, "x2": 30, "y2": 30}],
            evidence_note="reference",
            gold_locked=True,
        ),
    )
    assert bbox_response["prediction"]["matched_text"] == "search"

    with pytest.raises(api_app.HTTPException) as exc_info:
        api_app.save_bounding_box_audit_review(
            "audit-1",
            "BBOX-001",
            api_app.BoundingBoxAuditReviewRequest(
                reviewer_id="colleague",
                applicability="SINGLE_REGION",
                gold_boxes=[{"x1": 20, "y1": 20, "x2": 40, "y2": 40}],
                evidence_note="changed",
                gold_locked=True,
            ),
        )
    assert exc_info.value.status_code == 400

    metrics = api_app.get_evaluation_audit_metrics("audit-1", "colleague")
    assert metrics["ui_evaluability_agreement"]["accuracy"] == 1
    assert metrics["bounding_box_localization"]["overall"]["n_reviewed"] == 1


def test_inspection_api_reveals_manual_pipeline_comparison_and_bbox(tmp_path: Path, monkeypatch) -> None:
    audit_root = tmp_path / "audits"
    _audit_files(audit_root)
    monkeypatch.setattr(api_app, "EVALUATION_AUDIT_ROOT", audit_root)

    ui = api_app.get_ui_evaluability_inspection_items("audit-1")
    assert ui["blind"] is False
    assert ui["inspection_mode"] is True
    assert ui["items"][0]["manual_label"] == "PARTIALLY_UI_VERIFIABLE"
    assert ui["items"][0]["pipeline_label"] in {
        "UI_VERIFIABLE",
        "PARTIALLY_UI_VERIFIABLE",
        "NOT_UI_VERIFIABLE",
    }
    assert ui["items"][0]["labels_match"] == (
        ui["items"][0]["manual_label"] == ui["items"][0]["pipeline_label"]
    )

    bbox = api_app.get_bounding_box_inspection_items("audit-1")
    assert bbox["blind"] is False
    assert bbox["inspection_mode"] is True
    assert bbox["items"][0]["prediction"]["matched_text"] == "search"
    assert bbox["items"][0]["all_suggestions"] == []

    saved = api_app.save_bounding_box_inspection_judgment(
        "audit-1",
        "BBOX-001",
        api_app.BoundingBoxInspectionJudgmentRequest(
            status="incorrect",
            note="The title is not the supporting dietary-policy link.",
        ),
    )
    assert saved["inspection_judgment"]["status"] == "INCORRECT"
    refreshed = api_app.get_bounding_box_inspection_items("audit-1")
    assert refreshed["items"][0]["inspection_judgment"]["note"].startswith("The title")


def test_partial_ui_metrics_do_not_leak_hidden_reference(tmp_path: Path, monkeypatch) -> None:
    audit_root = tmp_path / "audits"
    audit_dir = _audit_files(audit_root)
    manifest = json.loads((audit_dir / "ui_manifest.json").read_text(encoding="utf-8"))
    manifest["items"].append({**manifest["items"][0], "audit_item_id": "UI-002", "requirement_id": "REQ-2"})
    manifest["sample_size"] = 2
    write_json(audit_dir / "ui_manifest.json", manifest)
    reference = json.loads((audit_dir / "ui_reference.json").read_text(encoding="utf-8"))
    reference["items"]["UI-002"] = {"gold_label": "UI_VERIFIABLE"}
    write_json(audit_dir / "ui_reference.json", reference)
    monkeypatch.setattr(api_app, "EVALUATION_AUDIT_ROOT", audit_root)

    api_app.save_ui_evaluability_audit_review(
        "audit-1",
        "UI-001",
        api_app.UiEvaluabilityAuditReviewRequest(
            reviewer_id="colleague",
            label="PARTIALLY_UI_VERIFIABLE",
        ),
    )
    agreement = api_app.get_evaluation_audit_metrics("audit-1", "colleague")["ui_evaluability_agreement"]
    assert agreement == {
        "status": "pending",
        "reviewed": 1,
        "required": 2,
        "reason": "Agreement is withheld until the blinded UI review is complete.",
    }
