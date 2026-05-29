from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/evaluate_claim_decomposition_external.py")


def _run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env.pop("GEMINI_API_KEY", None)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
    )


def _diagnostics_path(out: Path) -> Path:
    return out.with_suffix(".diagnostics.json")


def test_malformed_json_is_skipped_by_default_and_diagnostics_contain_it(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text('{"requirement_text": "broken"', encoding="utf-8")
    (tmp_path / "good.json").write_text(
        json.dumps({"requirement_text": "The system shall show a confirmation banner."}),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"

    result = _run(tmp_path, "--input", str(tmp_path), "--out", str(out))

    assert result.returncode == 0
    assert out.exists()
    assert len(json.loads(out.read_text())) == 1
    diagnostics = json.loads(_diagnostics_path(out).read_text())
    assert len(diagnostics["skipped_files"]) == 1
    assert diagnostics["skipped_files"][0]["exception_type"] == "JSONDecodeError"


def test_malformed_json_raises_when_fail_on_parse_error_is_set(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text('{"requirement_text": "broken"', encoding="utf-8")
    out = tmp_path / "out.json"

    result = _run(tmp_path, "--input", str(tmp_path), "--out", str(out), "--fail-on-parse-error")

    assert result.returncode != 0
    assert "JSONDecodeError" in result.stderr


def test_missing_explicit_file_path_fails_clearly(tmp_path: Path) -> None:
    missing = tmp_path / "missing.arff"
    out = tmp_path / "out.json"

    result = _run(tmp_path, "--input", str(missing), "--out", str(out))

    assert result.returncode == 2
    assert f"Input file does not exist: {missing}" in result.stderr
    assert not out.exists()


def test_empty_directory_writes_empty_output_and_diagnostics(tmp_path: Path) -> None:
    out = tmp_path / "out.json"

    result = _run(tmp_path, "--input", str(tmp_path), "--out", str(out))

    assert result.returncode == 0
    assert json.loads(out.read_text()) == []
    diagnostics = json.loads(_diagnostics_path(out).read_text())
    assert diagnostics["candidate_files"] == []


def test_valid_json_with_requirement_text_extracts_items(tmp_path: Path) -> None:
    (tmp_path / "req.json").write_text(
        json.dumps({"requirement_text": "The system shall display the checkout total."}),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"

    result = _run(tmp_path, "--input", str(tmp_path), "--out", str(out))

    assert result.returncode == 0
    items = json.loads(out.read_text())
    assert len(items) == 1
    assert items[0]["text"] == "The system shall display the checkout total."


def test_rule_guided_llm_cli_falls_back_without_api_key(tmp_path: Path) -> None:
    (tmp_path / "req.json").write_text(
        json.dumps({"requirement_text": "The system shall display the checkout total."}),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"

    result = _run(
        tmp_path,
        "--input",
        str(tmp_path),
        "--out",
        str(out),
        "--claim-decomposer",
        "rule_guided_llm",
        "--no-cache",
    )

    assert result.returncode == 0
    items = json.loads(out.read_text())
    assert len(items) == 1
    assert items[0]["claim_decomposer"] == "rule_guided_llm"
    assert "LLM_UNAVAILABLE" in items[0]["quality_flags"]
    assert items[0]["structured_claims"][0]["claim_text"] == "The system displays the checkout total."


def test_valid_json_with_no_requirement_fields_parses_zero_items(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text(json.dumps({"image": "step_01.png"}), encoding="utf-8")
    out = tmp_path / "out.json"

    result = _run(tmp_path, "--input", str(tmp_path), "--out", str(out))

    assert result.returncode == 0
    assert json.loads(out.read_text()) == []
    diagnostics = json.loads(_diagnostics_path(out).read_text())
    assert len(diagnostics["parsed_files"]) == 1
    assert diagnostics["parsed_files"][0]["num_extracted"] == 0


def test_xml_req_extracts_requirement_text(tmp_path: Path) -> None:
    (tmp_path / "pure.xml").write_text(
        "<root><req id='R1'>The system shall show passenger details.</req></root>",
        encoding="utf-8",
    )
    out = tmp_path / "out.json"

    result = _run(tmp_path, "--input", str(tmp_path), "--source-kind", "pure", "--out", str(out))

    assert result.returncode == 0
    items = json.loads(out.read_text())
    assert len(items) == 1
    assert items[0]["id"] == "R1"


def test_arff_attribute_text_extracts_requirement_text(tmp_path: Path) -> None:
    (tmp_path / "Promise+.arff").write_text(
        "\n".join(
            [
                "@relation requirements",
                "@attribute id string",
                "@attribute text string",
                "@attribute class {F,NF}",
                "@data",
                "1,\"The system shall allow users to reset passwords.\",F",
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.json"

    result = _run(tmp_path, "--input", str(tmp_path / "Promise+.arff"), "--out", str(out))

    assert result.returncode == 0
    items = json.loads(out.read_text())
    assert len(items) == 1
    assert items[0]["text"] == "The system shall allow users to reset passwords."
    diagnostics = json.loads(_diagnostics_path(out).read_text())
    metadata = diagnostics["parsed_files"][0]["metadata"]
    assert metadata["attribute_names"] == ["id", "text", "class"]
    assert metadata["selected_text_column"] == "text"
    assert metadata["parsed_arff_data_rows"] == 1


def test_csv_user_story_column_extracts_user_stories(tmp_path: Path) -> None:
    (tmp_path / "stories.csv").write_text(
        "id,user_story,label\nS1,As a user I want to save favorites so that I can revisit them later.,keep\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.json"

    result = _run(tmp_path, "--input", str(tmp_path), "--source-kind", "user_stories", "--out", str(out))

    assert result.returncode == 0
    items = json.loads(out.read_text())
    assert len(items) == 1
    assert items[0]["id"] == "S1"
    assert "save favorites" in items[0]["text"]


def test_output_and_diagnostics_are_written_for_valid_directories(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text(json.dumps({"image": "step_01.png"}), encoding="utf-8")
    out = tmp_path / "nested" / "out.json"

    result = _run(tmp_path, "--input", str(tmp_path), "--out", str(out))

    assert result.returncode == 0
    assert out.exists()
    assert _diagnostics_path(out).exists()
