from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
LOCAL_SPEC = importlib.util.spec_from_file_location(
    "run_smolvlm_open_baseline", SCRIPT_DIR / "run_smolvlm_open_baseline.py"
)
assert LOCAL_SPEC and LOCAL_SPEC.loader
LOCAL_MODULE = importlib.util.module_from_spec(LOCAL_SPEC)
LOCAL_SPEC.loader.exec_module(LOCAL_MODULE)

import sys

sys.modules["run_smolvlm_open_baseline"] = LOCAL_MODULE
SPEC = importlib.util.spec_from_file_location(
    "run_openrouter_qwen_baseline", SCRIPT_DIR / "run_openrouter_qwen_baseline.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_image_data_url_resizes_and_encodes(tmp_path: Path) -> None:
    from PIL import Image

    path = tmp_path / "large.png"
    Image.new("RGB", (2000, 1000), "white").save(path)

    value = MODULE._image_data_url(path, longest_edge=500, jpeg_quality=80)

    assert value.startswith("data:image/jpeg;base64,")


def test_response_text_reads_chat_completion() -> None:
    assert MODULE._response_text(
        {"choices": [{"message": {"content": '{"claims":[]}'}}]}
    ) == '{"claims":[]}'
