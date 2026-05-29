from __future__ import annotations

import argparse
import csv
import fnmatch
import glob
import json
import re
import statistics
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from ui_verifier.requirements.claim_decomposition import (
    RuleGuidedLLMClaimDecomposer,
    decompose_requirement,
)


SUPPORTED_SUFFIXES = {".json", ".jsonl", ".xml", ".txt", ".csv", ".arff"}
DEFAULT_EXCLUDE_GLOBS = [
    "data/generated/pure_gui_artifact_review/**",
    "data/generated/**/*.zip",
    "**/*.png",
    "**/*.jpg",
    "**/*.jpeg",
    "**/*.webp",
    "**/__pycache__/**",
    ".git/**",
]
TEXT_FIELDS = [
    "requirement_text",
    "text",
    "description",
    "body",
    "requirement",
    "sentence",
    "user_story",
    "story",
]
CSV_TEXT_FIELDS = [
    "text",
    "requirement",
    "requirement_text",
    "story",
    "user_story",
    "description",
    "sentence",
]
ID_FIELDS = ["id", "requirement_id", "req_id", "story_id", "uid"]
ARFF_TEXT_FIELDS = [
    "requirementtext",
    "requirement",
    "text",
    "sentence",
    "requirement_text",
]

SPLIT_MARKERS = [
    " including ",
    " so users can ",
    " so that ",
    " while requiring ",
    " without requiring ",
    " and immediately ",
    " and visibly ",
    " and display ",
    " and displays ",
    " and show ",
    " and shows ",
    " and present ",
    " and presents ",
]

BAD_FRAGMENT_PATTERNS = [
    r"\babout monthly\.$",
    r"\bdisplay yearly\b",
    r"\breview to\b",
    r"\band display information about monthly\.",
    r"\bshall\b",
]

HIDDEN_OR_NON_UI_TERMS = [
    "backend",
    "database",
    "security",
    "encrypted",
    "license",
    "licensed",
    "gpl",
    "lgpl",
    "java",
    "swing",
    "platform independent",
    "payment processing",
    "email delivery",
    "send a confirmation",
    "approval check",
    "eligibility",
    "uptime",
    "performance",
]


@dataclass
class ExtractionContext:
    min_words: int
    max_words: int
    allow_long_text: bool


@dataclass
class ParseResult:
    items: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower().rstrip("."))


def is_copied_single(original: str, claims: list[str]) -> bool:
    return len(claims) == 1 and normalize(original) == normalize(claims[0])


def has_unresolved_marker(original: str, claims: list[str]) -> bool:
    original_l = f" {original.lower()} "
    return any(marker in original_l for marker in SPLIT_MARKERS) and len(claims) <= 1


def has_bad_fragment(claims: list[str]) -> bool:
    for claim in claims:
        c = claim.lower().strip()
        for pattern in BAD_FRAGMENT_PATTERNS:
            if re.search(pattern, c):
                return True
    return False


def has_hidden_or_non_ui_terms(text: str) -> bool:
    t = text.lower()
    return any(term in t for term in HIDDEN_OR_NON_UI_TERMS)


def is_requirement_like_text(
    text: str,
    *,
    min_words: int = 4,
    max_words: int = 120,
    allow_long_text: bool = False,
) -> bool:
    text = " ".join(str(text).split()).strip()
    if not text:
        return False
    words = text.split()
    if len(words) < min_words:
        return False
    if not allow_long_text and len(words) > max_words:
        return False
    lower = text.lower()
    if re.search(r"\.(png|jpg|jpeg|webp|gif|zip|json|xml|csv|arff)$", lower):
        return False
    if re.match(r"^[\w./\\:-]+\.(png|jpg|jpeg|webp|gif|zip|json|xml|csv|arff)$", lower):
        return False
    pathish_chars = sum(1 for ch in text if ch in "/\\{}[]<>|")
    if pathish_chars / max(len(text), 1) > 0.15:
        return False
    if re.fullmatch(r"[\d\s.,:-]+", text):
        return False
    code_chars = sum(1 for ch in text if ch in "{}[]();=<>")
    if code_chars / max(len(text), 1) > 0.18:
        return False
    if lower.startswith(("```", "{", "[", "<html", "<?xml")):
        return False
    if len(text) > 180 and re.search(r"[A-Za-z0-9+/]{120,}={0,2}", text):
        return False
    return True


def _clean_text(value: Any) -> str:
    return " ".join(str(value).split()).strip()


def _make_item(
    *,
    path: Path,
    text: str,
    item_id: Any,
    source_suffix: str = "",
) -> dict[str, str] | None:
    text = _clean_text(text)
    if not text:
        return None
    return {
        "id": str(item_id),
        "source": f"{path.stem}{source_suffix}",
        "source_file": str(path),
        "text": text,
    }


def read_jsonl(path: Path, ctx: ExtractionContext) -> ParseResult:
    out: list[dict[str, str]] = []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            continue
        text = _first_requirement_text(obj, ctx)
        if text is None:
            continue
        item = _make_item(
            path=path,
            text=text,
            item_id=obj.get("id") or obj.get("requirement_id") or f"{path.stem}-{line_no}",
        )
        if item:
            out.append(item)
    return ParseResult(out, {"jsonl_lines": len(lines)})


def read_json(path: Path, ctx: ExtractionContext) -> ParseResult:
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    out: list[dict[str, str]] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            text = _first_requirement_text(obj, ctx)
            if text is not None:
                item = _make_item(
                    path=path,
                    text=text,
                    item_id=obj.get("id") or obj.get("requirement_id") or obj.get("req_id") or len(out) + 1,
                )
                if item:
                    out.append(item)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return ParseResult(out, {"json_type": type(data).__name__})


def _first_requirement_text(obj: dict[str, Any], ctx: ExtractionContext) -> str | None:
    for field_name in TEXT_FIELDS:
        value = obj.get(field_name)
        if isinstance(value, str) and is_requirement_like_text(
            value,
            min_words=ctx.min_words,
            max_words=ctx.max_words,
            allow_long_text=ctx.allow_long_text,
        ):
            return value
    return None


def read_xml(path: Path, ctx: ExtractionContext) -> ParseResult:
    root = ET.parse(path).getroot()
    out: list[dict[str, str]] = []
    for i, elem in enumerate(root.iter(), 1):
        tag = elem.tag.lower().split("}")[-1]
        if tag not in {"req", "requirement"}:
            continue
        text = " ".join("".join(elem.itertext()).split())
        if not is_requirement_like_text(
            text,
            min_words=ctx.min_words,
            max_words=ctx.max_words,
            allow_long_text=ctx.allow_long_text,
        ):
            continue
        item = _make_item(
            path=path,
            text=text,
            item_id=elem.attrib.get("id") or elem.attrib.get("req_id") or f"{path.stem}-{i}",
        )
        if item:
            out.append(item)
    return ParseResult(out, {"root_tag": root.tag, "requirement_tags_extracted": len(out)})


def read_txt(path: Path, ctx: ExtractionContext) -> ParseResult:
    out: list[dict[str, str]] = []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i, line in enumerate(lines, 1):
        if not is_requirement_like_text(
            line,
            min_words=ctx.min_words,
            max_words=ctx.max_words,
            allow_long_text=ctx.allow_long_text,
        ):
            continue
        item = _make_item(path=path, text=line, item_id=f"{path.stem}-{i}")
        if item:
            out.append(item)
    return ParseResult(out, {"txt_lines": len(lines)})


def _parse_attribute_name(line: str) -> str | None:
    match = re.match(r"@attribute\s+('[^']+'|\"[^\"]+\"|\S+)", line.strip(), flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip("'\"")


def _parse_arff_row(line: str) -> list[str]:
    candidates: list[list[str]] = []
    for quotechar in ('"', "'"):
        try:
            candidates.append(next(csv.reader([line], quotechar=quotechar, escapechar="\\")))
        except csv.Error:
            continue
    if not candidates:
        return []
    return max(candidates, key=len)


def _select_text_column(attribute_names: list[str], preferred: list[str]) -> int | None:
    lower_names = [name.strip().lower().replace(" ", "_") for name in attribute_names]
    compact_names = [name.replace("_", "") for name in lower_names]
    preferred_compact = [name.lower().replace("_", "") for name in preferred]
    for wanted in preferred_compact:
        if wanted in compact_names:
            return compact_names.index(wanted)
    return None


def _longest_text_like_cell(row: list[str], ctx: ExtractionContext, skip_indices: set[int] | None = None) -> str | None:
    skip_indices = skip_indices or set()
    candidates = [
        cell.strip()
        for idx, cell in enumerate(row)
        if idx not in skip_indices
        and is_requirement_like_text(
            cell,
            min_words=ctx.min_words,
            max_words=ctx.max_words,
            allow_long_text=ctx.allow_long_text,
        )
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda value: len(value.split()))


def read_arff(path: Path, ctx: ExtractionContext) -> ParseResult:
    out: list[dict[str, str]] = []
    attribute_names: list[str] = []
    data_rows = 0
    in_data = False

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            continue
        if not in_data and s.lower().startswith("@attribute"):
            attribute_name = _parse_attribute_name(s)
            if attribute_name:
                attribute_names.append(attribute_name)
            continue
        if s.lower() == "@data":
            in_data = True
            continue
        if not in_data or s.startswith("@"):
            continue

        data_rows += 1
        row = _parse_arff_row(s)
        if not row:
            continue

        text_column = _select_text_column(attribute_names, ARFF_TEXT_FIELDS) if attribute_names else None
        text: str | None = None
        if text_column is not None and text_column < len(row):
            candidate = row[text_column].strip()
            if is_requirement_like_text(
                candidate,
                min_words=ctx.min_words,
                max_words=ctx.max_words,
                allow_long_text=ctx.allow_long_text,
            ):
                text = candidate
        if text is None:
            label_indices = {
                idx
                for idx, name in enumerate(attribute_names)
                if name.lower() in {"class", "label", "type", "category"}
            }
            text = _longest_text_like_cell(row, ctx, skip_indices=label_indices)
        if text is None:
            continue

        item = _make_item(path=path, text=text, item_id=f"{path.stem}-{len(out) + 1}")
        if item:
            out.append(item)

    selected_index = _select_text_column(attribute_names, ARFF_TEXT_FIELDS) if attribute_names else None
    return ParseResult(
        out,
        {
            "attribute_names": attribute_names,
            "selected_text_column": attribute_names[selected_index] if selected_index is not None else None,
            "parsed_arff_data_rows": data_rows,
            "extracted_requirements": len(out),
        },
    )


def read_csv(path: Path, ctx: ExtractionContext) -> ParseResult:
    out: list[dict[str, str]] = []
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if not raw.strip():
        return ParseResult([], {"csv_rows": 0, "selected_text_column": None})

    sample = raw[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel

    rows = list(csv.reader(raw.splitlines(), dialect))
    if not rows:
        return ParseResult([], {"csv_rows": 0, "selected_text_column": None})

    header = [cell.strip() for cell in rows[0]]
    text_index = _select_text_column(header, CSV_TEXT_FIELDS)
    id_index = _select_text_column(header, ID_FIELDS)
    data_rows = rows[1:] if text_index is not None else rows

    for row_no, row in enumerate(data_rows, start=2 if text_index is not None else 1):
        if not row:
            continue
        text: str | None = None
        if text_index is not None and text_index < len(row):
            candidate = row[text_index].strip()
            if is_requirement_like_text(
                candidate,
                min_words=ctx.min_words,
                max_words=ctx.max_words,
                allow_long_text=ctx.allow_long_text,
            ):
                text = candidate
        if text is None:
            text = _longest_text_like_cell(row, ctx)
        if text is None:
            continue

        item_id: Any = f"{path.stem}-{row_no}"
        if id_index is not None and id_index < len(row) and row[id_index].strip():
            item_id = row[id_index].strip()
        item = _make_item(path=path, text=text, item_id=item_id)
        if item:
            out.append(item)

    return ParseResult(
        out,
        {
            "csv_rows": max(0, len(data_rows)),
            "header": header if text_index is not None else None,
            "selected_text_column": header[text_index] if text_index is not None else None,
            "extracted_requirements": len(out),
        },
    )


def read_any(path: Path, ctx: ExtractionContext) -> ParseResult:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return read_jsonl(path, ctx)
    if suffix == ".json":
        return read_json(path, ctx)
    if suffix == ".xml":
        return read_xml(path, ctx)
    if suffix == ".txt":
        return read_txt(path, ctx)
    if suffix == ".csv":
        return read_csv(path, ctx)
    if suffix == ".arff":
        return read_arff(path, ctx)
    return ParseResult([], {"unsupported_suffix": suffix})


def _posix(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def _is_excluded(path: Path, patterns: list[str]) -> bool:
    value = _posix(path)
    return any(fnmatch.fnmatch(value, pattern) for pattern in patterns)


def discover_files(args: argparse.Namespace) -> tuple[list[Path], list[str]]:
    exclude_globs = [*DEFAULT_EXCLUDE_GLOBS, *(args.exclude_glob or [])]
    files: set[Path] = set()
    warnings: list[str] = []

    for pattern in args.include_glob or []:
        for match in glob.glob(pattern, recursive=True):
            path = Path(match)
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES and not _is_excluded(path, exclude_globs):
                files.add(path)

    for raw in args.input:
        path = Path(raw)
        if path.is_file():
            if path.suffix.lower() in SUPPORTED_SUFFIXES and not _is_excluded(path, exclude_globs):
                files.add(path)
            continue
        if path.is_dir():
            for candidate in sorted(path.rglob("*")):
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES:
                    if not _is_excluded(candidate, exclude_globs):
                        files.add(candidate)
            continue
        if len(args.input) == 1 and not args.include_glob:
            raise FileNotFoundError(f"Input file does not exist: {raw}")
        warnings.append(f"Input path does not exist and was ignored: {raw}")

    sorted_files = sorted(files, key=lambda p: _posix(p))
    return sorted_files, warnings


def diagnostics_path(out_path: Path) -> Path:
    return out_path.with_suffix(".diagnostics.json")


def _skip_entry(path: Path, reason: str, exc: BaseException | None = None) -> dict[str, str]:
    entry = {"path": str(path), "reason": reason}
    if exc is not None:
        entry["exception_type"] = exc.__class__.__name__
        entry["message"] = str(exc)
    return entry


def evaluate_items(
    items: list[dict[str, str]],
    *,
    claim_decomposer: str = "rule_based",
    llm_model: str | None = None,
    use_cache: bool = True,
    strict_llm: bool = False,
) -> list[dict[str, Any]]:
    results = []
    llm_decomposer: RuleGuidedLLMClaimDecomposer | None = None
    if claim_decomposer == "rule_guided_llm":
        llm_decomposer = RuleGuidedLLMClaimDecomposer(
            model_name=llm_model,
            use_cache=use_cache,
            strict=strict_llm,
        )
    elif claim_decomposer != "rule_based":
        raise ValueError(f"Unsupported claim decomposer: {claim_decomposer}")

    for item in items:
        structured_result = None
        if llm_decomposer is not None:
            structured_result = llm_decomposer.decompose(item["text"])
            claims = [claim.claim_text for claim in structured_result.claims]
        else:
            claims = decompose_requirement(item["text"])
        results.append(
            {
                **item,
                "num_words": len(item["text"].split()),
                "num_claims": len(claims),
                "claims": claims,
                "claim_decomposer": claim_decomposer,
                "structured_claims": (
                    [claim.model_dump(mode="json") for claim in structured_result.claims]
                    if structured_result is not None
                    else []
                ),
                "rule_based_claims": structured_result.rule_based_claims if structured_result is not None else claims,
                "quality_flags": structured_result.quality_flags if structured_result is not None else [],
                "detected_patterns": structured_result.detected_patterns if structured_result is not None else [],
                "prompt_version": structured_result.prompt_version if structured_result is not None else None,
                "model_name": structured_result.model_name if structured_result is not None else None,
                "cache_key": structured_result.cache_key if structured_result is not None else None,
                "raw_response_path": structured_result.raw_response_path if structured_result is not None else None,
                "notes": structured_result.notes if structured_result is not None else None,
                "flags": {
                    "copied_single": is_copied_single(item["text"], claims),
                    "long_single": len(claims) == 1 and len(item["text"].split()) >= 22,
                    "bad_fragment": has_bad_fragment(claims),
                    "unresolved_marker": has_unresolved_marker(item["text"], claims),
                    "has_hidden_or_non_ui_terms": has_hidden_or_non_ui_terms(item["text"]),
                },
            }
        )
    return results


def _flag_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        for flag, value in result.get("flags", {}).items():
            counts[flag] = counts.get(flag, 0) + int(bool(value))
    return counts


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Evaluate rule-based requirement claim decomposition on external datasets."
    )
    ap.add_argument("--input", action="append", required=True, help="File or directory.")
    ap.add_argument("--include-glob", action="append", default=[], help="Additional glob to include. May repeat.")
    ap.add_argument("--exclude-glob", action="append", default=[], help="Additional glob to exclude. May repeat.")
    ap.add_argument("--source-kind", choices=["generic", "pure", "promise", "user_stories"], default="generic")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-words", type=int, default=4)
    ap.add_argument("--max-words", type=int, default=120)
    ap.add_argument("--allow-long-text", action="store_true")
    ap.add_argument("--claim-decomposer", choices=["rule_based", "rule_guided_llm"], default="rule_based")
    ap.add_argument("--llm-model", default=None)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--strict-llm", action="store_true")
    ap.add_argument("--fail-on-parse-error", action="store_true")
    return ap.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    diag_path = diagnostics_path(out_path)
    ctx = ExtractionContext(
        min_words=args.min_words,
        max_words=args.max_words,
        allow_long_text=args.allow_long_text,
    )

    candidate_files, input_warnings = discover_files(args)
    parsed_files: list[dict[str, Any]] = []
    skipped_files: list[dict[str, str]] = []
    extraction_counts: dict[str, int] = {}
    items: list[dict[str, str]] = []

    for warning in input_warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    for file in candidate_files:
        try:
            parsed = read_any(file, ctx)
        except Exception as exc:
            if args.fail_on_parse_error:
                raise
            reason = "parse_error"
            if isinstance(exc, JSONDecodeError):
                reason = f"json_decode_error at line {exc.lineno}, column {exc.colno}"
            entry = _skip_entry(file, reason, exc)
            skipped_files.append(entry)
            print(
                f"Warning: skipped {file}: {entry['reason']} ({entry.get('exception_type', 'Error')})",
                file=sys.stderr,
            )
            continue

        parsed_files.append(
            {
                "path": str(file),
                "num_extracted": len(parsed.items),
                "metadata": parsed.metadata,
            }
        )
        extraction_counts[str(file)] = len(parsed.items)
        items.extend(parsed.items)

    num_items_before_dedup = len(items)
    cleaned: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        text = _clean_text(item["text"])
        if not is_requirement_like_text(
            text,
            min_words=args.min_words,
            max_words=args.max_words,
            allow_long_text=args.allow_long_text,
        ):
            continue
        key = normalize(text)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({**item, "text": text})

    if args.limit:
        cleaned = cleaned[: args.limit]

    results = evaluate_items(
        cleaned,
        claim_decomposer=args.claim_decomposer,
        llm_model=args.llm_model,
        use_cache=not args.no_cache,
        strict_llm=args.strict_llm,
    )
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    diagnostics = {
        "input_args": vars(args),
        "candidate_files": [str(path) for path in candidate_files],
        "parsed_files": parsed_files,
        "skipped_files": skipped_files,
        "num_items_before_dedup": num_items_before_dedup,
        "num_items_after_dedup": len(cleaned),
        "extraction_counts_by_source_file": extraction_counts,
        "flag_counts": _flag_counts(results),
    }
    diag_path.write_text(json.dumps(diagnostics, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"candidate files found: {len(candidate_files)}")
    print(f"files parsed successfully: {len(parsed_files)}")
    print(f"files skipped: {len(skipped_files)}")
    print(f"extracted requirement candidates: {len(cleaned)}")
    print(f"output path: {out_path}")
    print(f"diagnostics path: {diag_path}")

    if args.source_kind == "pure":
        raw_pure_xml = [
            path
            for path in candidate_files
            if path.suffix.lower() == ".xml" and "generated" not in _posix(path).lower()
        ]
        if not raw_pure_xml and candidate_files:
            print(
                "Warning: source-kind pure found no non-generated XML files. Prefer raw PURE XML files with <req> tags.",
                file=sys.stderr,
            )

    if not candidate_files:
        print("No supported candidate files found. Check --input, --include-glob, and supported suffixes.")
        return 0
    if not results:
        print(
            "No requirements found. Possible causes: unsupported file structure, no requirement-like text fields, "
            "too-short rows, or filters such as --min-words/--max-words."
        )
        return 0

    claim_counts = [result["num_claims"] for result in results]
    print(f"items: {len(results)}")
    print(f"avg_claims: {statistics.mean(claim_counts):.2f}")
    print(f"median_claims: {statistics.median(claim_counts):.2f}")
    print(f"max_claims: {max(claim_counts)}")
    print()
    for flag, count in _flag_counts(results).items():
        print(f"{flag}: {count}/{len(results)} = {count / len(results):.1%}")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(parse_args(argv))
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
