import json
from pathlib import Path

from ui_verifier.api import flow_catalog
from ui_verifier.api.flow_catalog import FlowCatalog


def _write_step(path: Path) -> None:
    path.write_bytes(b"not an actual image")


def test_pure_flow_catalog_omits_non_gui_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(flow_catalog, "BASE_DIR", tmp_path)

    flow_dir = tmp_path / "flows" / "pure" / "pure_sample"
    flow_dir.mkdir(parents=True)
    _write_step(flow_dir / "step_01.png")
    _write_step(flow_dir / "step_02.png")
    (flow_dir / "task.json").write_text('{"website": "sample"}', encoding="utf-8")

    manifest_dir = tmp_path / "data" / "generated" / "pure_ui_dataset" / "pure_sample"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "artifact_manifest.json").write_text(
        json.dumps(
            {
                "flow_id": "pure_sample",
                "artifacts": [
                    {
                        "image_name": "step_01.png",
                        "classification_label": "NON_GUI_DIAGRAM",
                        "usable_for_requirement_evidence": False,
                    },
                    {
                        "image_name": "step_02.png",
                        "classification_label": "GUI_SCREEN",
                        "usable_for_requirement_evidence": True,
                        "page": 7,
                        "context_text": "Main window",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    catalog = FlowCatalog(flows_root=tmp_path / "flows")

    summaries = catalog.list_flows()
    assert len(summaries) == 1
    assert summaries[0]["num_steps"] == 1
    assert summaries[0]["step_indices"] == [2]

    steps = catalog.get_flow_steps("pure_sample")
    assert [step["image_name"] for step in steps] == ["step_02.png"]
    assert steps[0]["artifact_kind"] == "gui"
    assert steps[0]["artifact_label"] == "Gui Screen"
    assert steps[0]["artifact_page"] == 7
    assert steps[0]["artifact_context"] == "Main window"


def test_pure_flow_catalog_hides_flow_when_all_artifacts_are_non_gui(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(flow_catalog, "BASE_DIR", tmp_path)

    flow_dir = tmp_path / "flows" / "pure" / "pure_sample"
    flow_dir.mkdir(parents=True)
    _write_step(flow_dir / "step_01.png")
    (flow_dir / "task.json").write_text("{}", encoding="utf-8")

    manifest_dir = tmp_path / "data" / "generated" / "pure_ui_dataset" / "pure_sample"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "artifact_manifest.json").write_text(
        json.dumps(
            {
                "flow_id": "pure_sample",
                "artifacts": [
                    {
                        "image_name": "step_01.png",
                        "classification_label": "LOGO_DECORATIVE",
                        "usable_for_requirement_evidence": False,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    catalog = FlowCatalog(flows_root=tmp_path / "flows")

    assert catalog.list_flows() == []
    assert catalog.get_flow_steps("pure_sample") == []
