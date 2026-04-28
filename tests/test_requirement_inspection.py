from pathlib import Path

from ui_verifier.requirement_inspection.annotation_io import (
    load_annotation_records_csv,
    load_annotation_records_jsonl,
    save_annotation_records_csv,
    save_annotation_records_jsonl,
)
from ui_verifier.requirement_inspection.schemas import (
    AnnotationConfidence,
    NonEvaluableReason,
    RequirementInspectionRecord,
    RequirementInspectionType,
    UiEvaluability,
    VisibleSubtype,
)


def test_roundtrip_csv_and_jsonl(tmp_path: Path) -> None:
    records = [
        RequirementInspectionRecord(
            doc_id="pure_doc_001",
            req_id="REQ-001",
            requirement_text="The system shall display a confirmation message after saving.",
            requirement_type=RequirementInspectionType.FR,
            ui_evaluability=UiEvaluability.UI_VERIFIABLE,
            non_evaluable_reason=NonEvaluableReason.NONE,
            visible_subtype=VisibleSubtype.VALIDATION_OR_FEEDBACK,
            confidence=AnnotationConfidence.HIGH,
            notes="clearly visible after action",
        ),
        RequirementInspectionRecord(
            doc_id="pure_doc_001",
            req_id="REQ-002",
            requirement_text="The system shall encrypt user data at rest.",
            requirement_type=RequirementInspectionType.NFR,
            ui_evaluability=UiEvaluability.NOT_UI_VERIFIABLE,
            non_evaluable_reason=NonEvaluableReason.SECURITY_PRIVACY,
            visible_subtype=VisibleSubtype.NONE,
            confidence=AnnotationConfidence.HIGH,
        ),
    ]

    csv_path = tmp_path / "annotated_requirements.csv"
    jsonl_path = tmp_path / "annotated_requirements.jsonl"

    save_annotation_records_csv(records, csv_path)
    save_annotation_records_jsonl(records, jsonl_path)

    loaded_csv = load_annotation_records_csv(csv_path)
    loaded_jsonl = load_annotation_records_jsonl(jsonl_path)

    assert [record.to_dict() for record in loaded_csv] == [record.to_dict() for record in records]
    assert [record.to_dict() for record in loaded_jsonl] == [record.to_dict() for record in records]


def test_invalid_not_ui_verifiable_record_requires_reason() -> None:
    try:
        RequirementInspectionRecord(
            doc_id="pure_doc_001",
            req_id="REQ-003",
            requirement_text="The system shall be easy to use.",
            requirement_type=RequirementInspectionType.NFR,
            ui_evaluability=UiEvaluability.NOT_UI_VERIFIABLE,
            non_evaluable_reason=NonEvaluableReason.NONE,
            visible_subtype=VisibleSubtype.NONE,
            confidence=AnnotationConfidence.LOW,
        )
    except ValueError as exc:
        assert "non_evaluable_reason must not be NONE" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing non_evaluable_reason")
