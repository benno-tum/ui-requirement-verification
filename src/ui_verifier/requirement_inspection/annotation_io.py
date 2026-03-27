from __future__ import annotations

import csv
import json
from pathlib import Path

from ui_verifier.requirement_inspection.schemas import RequirementInspectionRecord


CSV_FIELDNAMES = [
    "doc_id",
    "req_id",
    "requirement_text",
    "requirement_type",
    "ui_evaluability",
    "non_evaluable_reason",
    "visible_subtype",
    "confidence",
    "notes",
]


def save_annotation_records_csv(records: list[RequirementInspectionRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_dict())


def load_annotation_records_csv(path: Path) -> list[RequirementInspectionRecord]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [RequirementInspectionRecord.from_dict(row) for row in reader]


def save_annotation_records_jsonl(records: list[RequirementInspectionRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


def load_annotation_records_jsonl(path: Path) -> list[RequirementInspectionRecord]:
    records: list[RequirementInspectionRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(RequirementInspectionRecord.from_dict(json.loads(line)))
    return records
