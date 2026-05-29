from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    url: str
    out_path: Path
    source_page: str
    note: str


DATASETS = {
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download public external requirement datasets.")
    parser.add_argument(
        "--dataset",
        choices=["all", *DATASETS.keys()],
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
    selected = DATASETS.values() if args.dataset == "all" else [DATASETS[args.dataset]]

    manifest: dict[str, dict[str, object]] = {}
    if args.manifest.exists():
        try:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}

    for spec in selected:
        size = _download(spec.url, spec.out_path, overwrite=args.overwrite)
        manifest[spec.key] = {
            "url": spec.url,
            "source_page": spec.source_page,
            "path": str(spec.out_path),
            "bytes": size,
            "note": spec.note,
        }

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"manifest: {args.manifest}")


if __name__ == "__main__":
    main()
