from pathlib import Path

from scripts.export_mind2web import BASE_DIR, path_for_metadata


def test_path_for_metadata_returns_repo_relative_path_for_repo_file() -> None:
    path = BASE_DIR / "data" / "annotations" / "flow_manifests" / "mind2web_repo_dataset_annotation_ids.txt"

    assert path_for_metadata(path) == "data/annotations/flow_manifests/mind2web_repo_dataset_annotation_ids.txt"


def test_path_for_metadata_accepts_relative_repo_path() -> None:
    path = Path("data/annotations/flow_manifests/mind2web_repo_dataset_annotation_ids.txt")

    assert path_for_metadata(path) == "data/annotations/flow_manifests/mind2web_repo_dataset_annotation_ids.txt"
