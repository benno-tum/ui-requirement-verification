from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from scripts.prepare_single_author_thesis_audits import (
    build_region_form,
    build_ui_form,
)
from scripts.apply_single_author_ui_evaluability_audit import reviewed_evidence_steps


def test_ui_disagreement_audit_contains_every_mismatch_and_explanations() -> None:
    form = build_ui_form()

    # The completed 81-item reinspection adopted the classifier label in 27
    # cases. Regenerating a form from the corrected references therefore leaves
    # 54 current disagreements; the archived completed form remains unchanged.
    assert len(form["items"]) == 54
    assert form["blind"] is False
    assert form["reference_fields_included"] is True
    assert form["pipeline_labels_included"] is True
    assert form["scope"]["source_item_count"] == 300
    for item in form["items"]:
        assert item["reference_label"] != item["pipeline_label"]
        assert item["pipeline_rationale"]
        assert item["divergence_hypothesis"]
        assert item["author_resolution"] is None
        assert item["author_final_label"] is None
        assert item["ordered_screenshots"]


def test_completed_ui_reinspection_preserves_all_original_decisions() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "data/annotations/evaluation_audits/single_author_final_20260725"
        / "ui_evaluability_disagreement_audit_form.json"
    )
    audit = json.loads(path.read_text(encoding="utf-8"))

    assert len(audit["items"]) == 81
    assert all(item["author_resolution"] for item in audit["items"])
    assert all(item["author_final_label"] for item in audit["items"])

    service_item = next(item for item in audit["items"] if item["audit_item_id"] == "UID-002")
    assert reviewed_evidence_steps(service_item) == [1, 2, 3]


def test_region_audit_has_four_groups_per_flow_and_all_no_region_cases() -> None:
    form = build_region_form(4)
    regular = [
        item
        for item in form["items"]
        if not item["selection_features"].get("explicit_no_visible_region")
    ]
    no_region = [
        item
        for item in form["items"]
        if item["selection_features"].get("explicit_no_visible_region")
    ]

    assert len(form["items"]) == 60
    assert sorted(Counter(item["flow_id"] for item in regular).values()) == [4] * 13
    assert len(no_region) == 8
    assert all(item["author_semantic_relevance"] is None for item in form["items"])
