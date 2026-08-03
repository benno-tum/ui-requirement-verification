from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    url: str
    out_path: Path
    source_page: str
    note: str
    license_id: str | None = None
    provenance_notice: str | None = None
    expected_md5: str | None = None
    extract_to: Path | None = None


PURE_PROVENANCE_NOTICE = (
    "The PURE record states that its curators did not verify the underlying rights "
    "of every collected Web document and provides a contact for takedown requests."
)


DATASETS = {
    "pure_xml": DatasetSpec(
        key="pure_xml",
        url="https://zenodo.org/api/records/7118517/files/requirements-xml.zip/content",
        out_path=Path("data/raw/pure/requirements-xml.zip"),
        source_page="https://zenodo.org/records/7118517",
        note="PURE 2.0 XML archive from Zenodo (DOI 10.5281/zenodo.7118517).",
        license_id="CC-BY-4.0",
        provenance_notice=PURE_PROVENANCE_NOTICE,
        expected_md5="c81235c40f88a2c947ae66e0eddad585",
        extract_to=Path("data/raw/pure"),
    ),
    "pure_documents": DatasetSpec(
        key="pure_documents",
        url="https://zenodo.org/api/records/7118517/files/requirements.zip/content",
        out_path=Path("data/raw/pure/requirements.zip"),
        source_page="https://zenodo.org/records/7118517",
        note="PURE 2.0 source-document archive from Zenodo (DOI 10.5281/zenodo.7118517).",
        license_id="CC-BY-4.0",
        provenance_notice=PURE_PROVENANCE_NOTICE,
        expected_md5="bc319fe28619f6290badff328ca159dd",
        extract_to=Path("data/raw/pure"),
    ),
    "pure_schema": DatasetSpec(
        key="pure_schema",
        url="https://zenodo.org/api/records/7118517/files/req_document.xsd/content",
        out_path=Path("data/raw/pure/req_document.xsd"),
        source_page="https://zenodo.org/records/7118517",
        note="XML schema distributed with PURE 2.0.",
        license_id="CC-BY-4.0",
        provenance_notice=PURE_PROVENANCE_NOTICE,
        expected_md5="f44c255db9414afb7c39265697abcb33",
    ),
    "promise_exp": DatasetSpec(
        key="promise_exp",
        url=(
            "https://raw.githubusercontent.com/AleksandarMitrevski/"
            "se-requirements-classification/master/0-datasets/PROMISE_exp/PROMISE_exp.arff"
        ),
        out_path=Path("data/external/promise_exp/PROMISE_exp.arff"),
        source_page="https://github.com/AleksandarMitrevski/se-requirements-classification",
        note=(
            "PROMISE_exp ARFF dataset. This is not the missing Promise+.arff file; "
            "it is a public expanded PROMISE dataset suitable for external decomposer checks."
        ),
    ),
    "user_stories_neodataset": DatasetSpec(
        key="user_stories_neodataset",
        url="https://huggingface.co/datasets/giseldo/neodataset/resolve/main/issues.csv",
        out_path=Path("data/external/user_stories/neodataset_issues.csv"),
        source_page="https://huggingface.co/datasets/giseldo/neodataset",
        note="NeoDataset user-story/issues CSV from Hugging Face.",
    ),
}

PURE_DATASET_KEYS = ("pure_xml", "pure_documents", "pure_schema")


def _download(url: str, out_path: Path, *, overwrite: bool = False) -> int:
    if out_path.exists() and not overwrite:
        print(f"exists: {out_path}")
        return out_path.stat().st_size

    out_path.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "ui-verifier-external-data-setup"})
    with urlopen(request, timeout=120) as response:
        data = response.read()
    out_path.write_bytes(data)
    print(f"downloaded: {out_path} ({len(data)} bytes)")
    return len(data)


def _md5(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - verifies the checksum published by Zenodo.
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_zip(archive: Path, destination: Path, *, overwrite: bool = False) -> int:
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    archive_files = 0
    with ZipFile(archive) as bundle:
        for member in bundle.infolist():
            relative = Path(member.filename)
            if member.is_dir() or "__MACOSX" in relative.parts or relative.name == ".DS_Store":
                continue
            archive_files += 1
            target = (destination / relative).resolve()
            if destination_root not in target.parents:
                raise ValueError(f"Unsafe archive member: {member.filename}")
            if target.exists() and not overwrite:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("wb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
    print(f"extracted: {archive} -> {destination} ({archive_files} archive files available)")
    return archive_files


def _selected_specs(dataset: str) -> list[DatasetSpec]:
    if dataset == "all":
        return list(DATASETS.values())
    if dataset == "pure":
        return [DATASETS[key] for key in PURE_DATASET_KEYS]
    return [DATASETS[dataset]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download public external requirement datasets.")
    parser.add_argument(
        "--dataset",
        choices=["all", "pure", *DATASETS.keys()],
        default="all",
        help="Dataset to download.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/external/source_manifest.json"),
        help="Where to write source metadata.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected = _selected_specs(args.dataset)

    manifest: dict[str, dict[str, object]] = {}
    if args.manifest.exists():
        try:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}

    for spec in selected:
        size = _download(spec.url, spec.out_path, overwrite=args.overwrite)
        checksum = _md5(spec.out_path)
        if spec.expected_md5 and checksum != spec.expected_md5:
            raise ValueError(
                f"Checksum mismatch for {spec.out_path}: expected {spec.expected_md5}, got {checksum}"
            )
        extracted_files = None
        if spec.extract_to is not None:
            extracted_files = _extract_zip(
                spec.out_path,
                spec.extract_to,
                overwrite=args.overwrite,
            )
        manifest[spec.key] = {
            "url": spec.url,
            "source_page": spec.source_page,
            "path": str(spec.out_path),
            "bytes": size,
            "md5": checksum,
            "license": spec.license_id,
            "provenance_notice": spec.provenance_notice,
            "extracted_to": str(spec.extract_to) if spec.extract_to else None,
            "extracted_files": extracted_files,
            "note": spec.note,
        }

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"manifest: {args.manifest}")


if __name__ == "__main__":
    main()
