from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest

import scripts.setup_external_requirement_data as setup_data


def test_pure_alias_selects_all_three_zenodo_files() -> None:
    specs = setup_data._selected_specs("pure")
    assert [spec.key for spec in specs] == [
        "pure_xml",
        "pure_documents",
        "pure_schema",
    ]
    assert all(spec.license_id == "CC-BY-4.0" for spec in specs)
    assert all(spec.provenance_notice == setup_data.PURE_PROVENANCE_NOTICE for spec in specs)


def test_zip_extraction_ignores_macos_metadata(tmp_path: Path) -> None:
    archive = tmp_path / "pure.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr("XMLZIPFile/example.xml", "<requirements />")
        bundle.writestr("__MACOSX/XMLZIPFile/._example.xml", "metadata")

    destination = tmp_path / "pure"
    assert setup_data._extract_zip(archive, destination) == 1
    assert (destination / "XMLZIPFile/example.xml").read_text() == "<requirements />"
    assert not (destination / "__MACOSX").exists()


def test_zip_extraction_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr("../outside.txt", "unsafe")

    with pytest.raises(ValueError, match="Unsafe archive member"):
        setup_data._extract_zip(archive, tmp_path / "destination")
