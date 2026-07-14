from __future__ import annotations

import base64
from io import BytesIO
import json
from pathlib import Path

from PIL import Image

from ui_verifier.api import app as api_app


def _png_base64() -> str:
    output = BytesIO()
    Image.new("RGB", (24, 16), color=(35, 91, 180)).save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def test_create_uploaded_flow_and_build_pipeline_command(tmp_path: Path, monkeypatch) -> None:
    base_dir = tmp_path / "repo"
    flows_root = base_dir / "data" / "processed" / "flows"
    generated_root = base_dir / "data" / "generated"
    monkeypatch.setattr(api_app, "BASE_DIR", base_dir)
    monkeypatch.setattr(api_app, "GENERATED_ROOT", generated_root)
    monkeypatch.setattr(api_app.flow_catalog, "flows_root", flows_root)

    created = api_app.create_uploaded_flow(
        api_app.CreateUploadedFlowRequest(
            project_name="Checkout UX",
            description="Verify the confirmation screen",
            requirements_content=json.dumps(
                [
                    {"id": "order-number", "text": "The confirmation shows an order number."},
                    "A return-to-store action is visible.",
                ]
            ),
            requirements_filename="requirements.json",
            screenshots=[
                api_app.UploadedScreenshot(filename="confirmation.png", content_base64=_png_base64()),
            ],
        )
    )

    flow_id = created["flow"]["flow_id"]
    assert flow_id.startswith("upload-checkout-ux-")
    assert created["requirements_count"] == 2
    assert created["steps"][0]["image_width"] == 24
    assert (flows_root / "uploads" / flow_id / "step_1.png").exists()

    requirements_path = generated_root / "uploaded_flows" / flow_id / "requirements.json"
    requirements_data = json.loads(requirements_path.read_text(encoding="utf-8"))
    assert [item["requirement_id"] for item in requirements_data["requirements"]] == [
        "order-number",
        "REQ-002",
    ]

    command, output_path = api_app.build_pipeline_run_command(
        flow_id,
        api_app.StartPipelineRunRequest(requirements_source="uploaded"),
        job_id="job-1",
    )
    assert command[command.index("--requirements-source") + 1] == "custom"
    assert command[command.index("--requirements") + 1] == str(requirements_path)
    assert output_path == generated_root / "ui_verification_runs" / f"{flow_id}.json"


def test_plain_text_requirements_remove_list_markers() -> None:
    requirements = api_app._normalize_uploaded_requirements(
        "# Requirements\n- First requirement\n2. Second requirement",
        "requirements.md",
        flow_id="upload-example-1234",
    )

    assert [item["text"] for item in requirements] == ["First requirement", "Second requirement"]
