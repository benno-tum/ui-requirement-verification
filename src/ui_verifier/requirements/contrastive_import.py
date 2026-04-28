from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import json
from json import JSONDecoder
from pathlib import Path
import re
from typing import Any

from ui_verifier.common.json_utils import load_json
from ui_verifier.requirements.schemas import CandidateRequirementFile, GoldRequirementFile, HarvestedRequirementFile


BASE_DIR = Path(__file__).resolve().parents[3]
DEFAULT_IMPORT_ROOT = BASE_DIR / "data" / "generated" / "contrastive_import"
DEFAULT_RAW_PATH = DEFAULT_IMPORT_ROOT / "raw" / "contrastive_dump.txt"
DEFAULT_PARSED_BLOCKS_PATH = DEFAULT_IMPORT_ROOT / "parsed_blocks.json"
DEFAULT_FLOW_CATALOG_PATH = DEFAULT_IMPORT_ROOT / "flow_catalog.json"
DEFAULT_MATCH_MANIFEST_PATH = DEFAULT_IMPORT_ROOT / "match_manifest.json"
DEFAULT_DUPLICATES_PATH = DEFAULT_IMPORT_ROOT / "duplicates.json"
DEFAULT_UNMATCHED_PATH = DEFAULT_IMPORT_ROOT / "unmatched_expected_flows.json"
DEFAULT_REPORT_PATH = DEFAULT_IMPORT_ROOT / "import_report.md"
DEFAULT_STAGED_ROOT = DEFAULT_IMPORT_ROOT / "staged"
DEFAULT_FLOW_ROOT = BASE_DIR / "data" / "processed" / "flows" / "mind2web"
DEFAULT_GOLD_ROOT = BASE_DIR / "data" / "annotations" / "requirements_gold"
DEFAULT_CANDIDATE_ROOT = BASE_DIR / "data" / "generated" / "candidate_requirements"


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    text = text.strip(" \t\r\n.,;:!?()[]{}\"'")
    return text


def normalize_for_tokens(value: str | None) -> list[str]:
    text = normalize_text(value)
    if not text:
        return []
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [token for token in text.split() if token]


def sequence_similarity(a: str | None, b: str | None) -> float:
    normalized_a = normalize_text(a)
    normalized_b = normalize_text(b)
    if not normalized_a or not normalized_b:
        return 0.0
    return SequenceMatcher(None, normalized_a, normalized_b).ratio()


def token_jaccard(a: str | None, b: str | None) -> float:
    tokens_a = set(normalize_for_tokens(a))
    tokens_b = set(normalize_for_tokens(b))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def combined_similarity(a: str | None, b: str | None) -> float:
    seq = sequence_similarity(a, b)
    jac = token_jaccard(a, b)
    return max(seq, jac * 0.95)


def _candidate_text_set(requirements: list[dict[str, Any]]) -> set[str]:
    return {
        normalize_text(item.get("candidate_text"))
        for item in requirements
        if normalize_text(item.get("candidate_text"))
    }


def _source_text_set(requirements: list[dict[str, Any]]) -> set[str]:
    return {
        normalize_text(item.get("source_gold_text"))
        for item in requirements
        if normalize_text(item.get("source_gold_text"))
    }


@dataclass(slots=True)
class ParsedContrastiveBlock:
    block_index: int
    flow_overview: str | None
    capability_summary: list[str]
    requirements: list[dict[str, Any]]
    raw_start_offset: int
    raw_end_offset: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_index": self.block_index,
            "flow_overview": self.flow_overview,
            "capability_summary": self.capability_summary,
            "requirements": self.requirements,
            "raw_start_offset": self.raw_start_offset,
            "raw_end_offset": self.raw_end_offset,
        }

    @property
    def source_gold_texts(self) -> list[str]:
        texts: list[str] = []
        for requirement in self.requirements:
            text = str(requirement.get("source_gold_text") or "").strip()
            if text:
                texts.append(text)
        return texts

    @property
    def candidate_texts(self) -> list[str]:
        texts: list[str] = []
        for requirement in self.requirements:
            text = str(requirement.get("candidate_text") or "").strip()
            if text:
                texts.append(text)
        return texts


@dataclass(slots=True)
class MatchResult:
    flow_id: str
    score: float
    reasons: list[str]


def parse_concatenated_json_blocks(raw_text: str) -> list[ParsedContrastiveBlock]:
    decoder = JSONDecoder()
    blocks: list[ParsedContrastiveBlock] = []
    index = 0
    block_index = 1

    while index < len(raw_text):
        while index < len(raw_text) and raw_text[index].isspace():
            index += 1
        if index >= len(raw_text):
            break

        if raw_text[index] != "{":
            next_object_start = raw_text.find("{", index + 1)
            if next_object_start == -1:
                break
            index = next_object_start
            continue

        try:
            parsed, end = decoder.raw_decode(raw_text, index)
        except json.JSONDecodeError:
            next_object_start = raw_text.find("{", index + 1)
            if next_object_start == -1:
                raise
            index = next_object_start
            continue
        if not isinstance(parsed, dict):
            raise ValueError(f"Parsed block {block_index} is not a JSON object.")

        requirements = parsed.get("requirements", [])
        if not isinstance(requirements, list):
            raise ValueError(f"Parsed block {block_index} has non-list requirements.")

        capability_summary = parsed.get("capability_summary", [])
        if not isinstance(capability_summary, list):
            capability_summary = []

        blocks.append(
            ParsedContrastiveBlock(
                block_index=block_index,
                flow_overview=str(parsed.get("flow_overview") or "").strip() or None,
                capability_summary=[str(item).strip() for item in capability_summary if str(item).strip()],
                requirements=[item for item in requirements if isinstance(item, dict)],
                raw_start_offset=index,
                raw_end_offset=end,
            )
        )
        index = end
        block_index += 1

    return blocks


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_flow_catalog(
    *,
    flow_root: Path = DEFAULT_FLOW_ROOT,
    gold_root: Path = DEFAULT_GOLD_ROOT,
    candidate_root: Path = DEFAULT_CANDIDATE_ROOT,
) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []

    for gold_path in sorted(gold_root.glob("*/gold_requirements.json")):
        flow_id = gold_path.parent.name
        flow_dir = flow_root / flow_id
        task_path = flow_dir / "task.json"
        task = load_json(task_path) if task_path.exists() else {}
        gold_file = GoldRequirementFile.load(gold_path)

        harvested_path = candidate_root / flow_id / "harvested_requirements.json"
        candidate_path = candidate_root / flow_id / "candidate_requirements.json"

        harvested = HarvestedRequirementFile.load(harvested_path) if harvested_path.exists() else None
        candidates = CandidateRequirementFile.load(candidate_path) if candidate_path.exists() else None

        catalog.append(
            {
                "flow_id": flow_id,
                "website": task.get("website"),
                "domain": task.get("domain"),
                "task_description": task.get("confirmed_task"),
                "gold_requirements": [
                    {
                        "requirement_id": req.requirement_id,
                        "text": req.text,
                    }
                    for req in gold_file.requirements
                ],
                "harvested_requirements": (
                    [
                        {
                            "harvest_id": req.harvest_id,
                            "text": req.harvested_text,
                        }
                        for req in harvested.requirements
                    ]
                    if harvested is not None
                    else []
                ),
                "candidate_requirements": (
                    [
                        {
                            "requirement_id": req.requirement_id,
                            "text": req.text,
                        }
                        for req in candidates.requirements
                    ]
                    if candidates is not None
                    else []
                ),
                "flow_overview": harvested.flow_overview if harvested is not None else (candidates.flow_overview if candidates is not None else None),
                "capability_summary": (
                    list(harvested.capability_summary)
                    if harvested is not None and harvested.capability_summary
                    else (list(candidates.capability_summary) if candidates is not None else [])
                ),
                "flow_dir": str(flow_dir),
                "_normalized_gold_texts": {
                    normalize_text(req.text): req.requirement_id for req in gold_file.requirements
                },
            }
        )

    return catalog


def _infer_website_hint(block: ParsedContrastiveBlock, catalog: list[dict[str, Any]]) -> str | None:
    overview = normalize_text(block.flow_overview)
    if not overview:
        return None
    candidates: list[str] = []
    for entry in catalog:
        website = normalize_text(entry.get("website"))
        if website and website in overview:
            candidates.append(str(entry.get("website")))
    if len(set(candidates)) == 1:
        return candidates[0]
    return None


def score_block_against_flow(block: ParsedContrastiveBlock, flow: dict[str, Any]) -> MatchResult:
    reasons: list[str] = []
    score = 0.0

    normalized_gold_texts: dict[str, str] = flow["_normalized_gold_texts"]
    distinct_exact_matches: set[str] = set()
    strong_matches = 0

    for source_text in block.source_gold_texts:
        normalized_source = normalize_text(source_text)
        if not normalized_source:
            continue

        best_similarity = 0.0
        best_gold_req_id: str | None = None
        best_gold_text: str | None = None
        for gold_text_norm, gold_req_id in normalized_gold_texts.items():
            similarity = combined_similarity(normalized_source, gold_text_norm)
            if similarity > best_similarity:
                best_similarity = similarity
                best_gold_req_id = gold_req_id
                best_gold_text = gold_text_norm

        if best_similarity >= 0.995:
            score += 150
            strong_matches += 1
            if best_gold_req_id is not None:
                distinct_exact_matches.add(best_gold_req_id)
            reasons.append(
                f"exact source_gold_text match for {best_gold_req_id}: {source_text}"
            )
        elif best_similarity >= 0.96:
            score += 110
            strong_matches += 1
            if best_gold_req_id is not None:
                distinct_exact_matches.add(best_gold_req_id)
            reasons.append(
                f"near-exact source_gold_text match for {best_gold_req_id}: {source_text}"
            )
        elif best_similarity >= 0.88:
            score += 45
            reasons.append(
                f"partial source_gold_text similarity ({best_similarity:.2f}) to {best_gold_req_id}: {source_text}"
            )
        elif best_gold_text:
            reasons.append(
                f"weak source_gold_text similarity ({best_similarity:.2f}) to {best_gold_req_id}"
            )

    if distinct_exact_matches:
        boost = len(distinct_exact_matches) * 70
        score += boost
        reasons.append(
            f"{len(distinct_exact_matches)} distinct gold requirements matched strongly (+{boost:.0f})"
        )
    elif strong_matches:
        boost = strong_matches * 20
        score += boost
        reasons.append(f"{strong_matches} strong source matches without distinct ids (+{boost:.0f})")

    block_overview_text = " ".join(
        [block.flow_overview or "", " ".join(block.capability_summary)]
    )
    flow_context_text = " ".join(
        [
            str(flow.get("task_description") or ""),
            str(flow.get("flow_overview") or ""),
            " ".join(flow.get("capability_summary") or []),
        ]
    )

    overview_similarity = combined_similarity(block_overview_text, flow_context_text)
    if overview_similarity >= 0.75:
        bonus = 40
        score += bonus
        reasons.append(f"strong overview/task similarity {overview_similarity:.2f} (+{bonus})")
    elif overview_similarity >= 0.55:
        bonus = 20
        score += bonus
        reasons.append(f"moderate overview/task similarity {overview_similarity:.2f} (+{bonus})")

    task_similarity = combined_similarity(block.flow_overview, flow.get("task_description"))
    if task_similarity >= 0.45:
        bonus = 15
        score += bonus
        reasons.append(f"task-description overlap {task_similarity:.2f} (+{bonus})")

    website = normalize_text(flow.get("website"))
    domain = normalize_text(flow.get("domain"))
    overview = normalize_text(block.flow_overview)
    capability_blob = normalize_text(" ".join(block.capability_summary))
    if website and (website in overview or website in capability_blob):
        score += 8
        reasons.append(f"website hint match '{flow.get('website')}' (+8)")
    if domain and (domain in overview or domain in capability_blob):
        score += 4
        reasons.append(f"domain hint match '{flow.get('domain')}' (+4)")

    return MatchResult(flow_id=str(flow["flow_id"]), score=score, reasons=reasons)


def classify_match(
    *,
    best: MatchResult,
    runner_up: MatchResult | None,
    block: ParsedContrastiveBlock,
) -> tuple[str, float]:
    score_gap = best.score - (runner_up.score if runner_up is not None else 0.0)
    distinct_source_count = len({normalize_text(text) for text in block.source_gold_texts if normalize_text(text)})

    if best.score < 160:
        return "unmatched", score_gap
    if runner_up is not None and best.score < 260 and score_gap < 120:
        return "ambiguous", score_gap
    if runner_up is not None and distinct_source_count < 2 and score_gap < 160:
        return "ambiguous", score_gap
    return "matched", score_gap


def _block_duplicate_similarity(block_a: ParsedContrastiveBlock, block_b: ParsedContrastiveBlock) -> dict[str, float]:
    source_a = _source_text_set(block_a.requirements)
    source_b = _source_text_set(block_b.requirements)
    source_overlap = 0.0
    if source_a and source_b:
        source_overlap = len(source_a & source_b) / len(source_a | source_b)

    candidate_a = _candidate_text_set(block_a.requirements)
    candidate_b = _candidate_text_set(block_b.requirements)
    candidate_overlap = 0.0
    if candidate_a and candidate_b:
        candidate_overlap = len(candidate_a & candidate_b) / len(candidate_a | candidate_b)

    overview_similarity = combined_similarity(block_a.flow_overview, block_b.flow_overview)
    capability_similarity = combined_similarity(
        " ".join(block_a.capability_summary),
        " ".join(block_b.capability_summary),
    )

    return {
        "source_overlap": source_overlap,
        "candidate_overlap": candidate_overlap,
        "overview_similarity": overview_similarity,
        "capability_similarity": capability_similarity,
    }


def detect_duplicates(
    blocks: list[ParsedContrastiveBlock],
    manifest_entries: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[int, int]]:
    by_block = {block.block_index: block for block in blocks}
    duplicates: list[dict[str, Any]] = []
    duplicate_map: dict[int, int] = {}

    flow_to_entries: dict[str, list[dict[str, Any]]] = {}
    for entry in manifest_entries:
        flow_id = entry.get("matched_flow_id")
        if not flow_id:
            continue
        if entry.get("status") not in {"matched", "ambiguous"}:
            continue
        flow_to_entries.setdefault(flow_id, []).append(entry)

    for flow_id, entries in flow_to_entries.items():
        if len(entries) < 2:
            continue

        ranked = sorted(
            entries,
            key=lambda item: (
                float(item.get("score") or 0.0),
                len(item.get("exact_source_gold_requirement_ids") or []),
                -int(item["block_index"]),
            ),
            reverse=True,
        )
        winner = ranked[0]
        winner_block = by_block[int(winner["block_index"])]

        for entry in ranked[1:]:
            candidate_block = by_block[int(entry["block_index"])]
            similarity = _block_duplicate_similarity(winner_block, candidate_block)
            if (
                similarity["source_overlap"] >= 0.45
                or similarity["overview_similarity"] >= 0.72
                or similarity["capability_similarity"] >= 0.72
            ):
                duplicate_map[int(entry["block_index"])] = int(winner["block_index"])
                duplicates.append(
                    {
                        "flow_id": flow_id,
                        "kept_block_index": int(winner["block_index"]),
                        "duplicate_block_index": int(entry["block_index"]),
                        "source_overlap": round(similarity["source_overlap"], 4),
                        "candidate_overlap": round(similarity["candidate_overlap"], 4),
                        "overview_similarity": round(similarity["overview_similarity"], 4),
                        "capability_similarity": round(similarity["capability_similarity"], 4),
                    }
                )

    return duplicates, duplicate_map


def create_match_manifest(
    blocks: list[ParsedContrastiveBlock],
    catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []

    for block in blocks:
        scored = sorted(
            (score_block_against_flow(block, flow) for flow in catalog),
            key=lambda result: result.score,
            reverse=True,
        )
        best = scored[0]
        runner_up = scored[1] if len(scored) > 1 else None
        status, score_gap = classify_match(best=best, runner_up=runner_up, block=block)

        exact_source_gold_requirement_ids: list[str] = []
        for reason in best.reasons:
            if reason.startswith("exact source_gold_text match for ") or reason.startswith("near-exact source_gold_text match for "):
                req_id = reason.split(" for ", 1)[1].split(":", 1)[0].strip()
                if req_id and req_id not in exact_source_gold_requirement_ids:
                    exact_source_gold_requirement_ids.append(req_id)

        manifest.append(
            {
                "block_index": block.block_index,
                "status": status,
                "matched_flow_id": best.flow_id if status != "unmatched" else None,
                "score": round(best.score, 4),
                "runner_up_flow_id": runner_up.flow_id if runner_up is not None else None,
                "runner_up_score": round(runner_up.score, 4) if runner_up is not None else None,
                "score_gap": round(score_gap, 4),
                "website_hint": _infer_website_hint(block, catalog),
                "flow_overview": block.flow_overview,
                "match_reasons": best.reasons[:8],
                "duplicate_of_block": None,
                "raw_start_offset": block.raw_start_offset,
                "raw_end_offset": block.raw_end_offset,
                "exact_source_gold_requirement_ids": exact_source_gold_requirement_ids,
            }
        )

    duplicates, duplicate_map = detect_duplicates(blocks, manifest)
    for entry in manifest:
        duplicate_of = duplicate_map.get(int(entry["block_index"]))
        if duplicate_of is not None:
            entry["status"] = "duplicate"
            entry["duplicate_of_block"] = duplicate_of

    return manifest


def build_duplicates_payload(
    blocks: list[ParsedContrastiveBlock],
    manifest: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    duplicates: list[dict[str, Any]] = []
    block_by_index = {block.block_index: block for block in blocks}
    by_flow: dict[str, list[dict[str, Any]]] = {}
    for entry in manifest:
        flow_id = entry.get("matched_flow_id")
        if flow_id:
            by_flow.setdefault(str(flow_id), []).append(entry)

    for flow_id, entries in by_flow.items():
        kept = [entry for entry in entries if entry.get("status") == "matched"]
        dupes = [entry for entry in entries if entry.get("status") == "duplicate"]
        if not dupes:
            continue
        kept_block = kept[0]["block_index"] if kept else dupes[0].get("duplicate_of_block")
        for dupe in dupes:
            kept = block_by_index[int(kept_block)]
            duplicate = block_by_index[int(dupe["block_index"])]
            similarity = _block_duplicate_similarity(kept, duplicate)
            duplicates.append(
                {
                    "flow_id": flow_id,
                    "kept_block_index": kept_block,
                    "duplicate_block_index": dupe["block_index"],
                    "duplicate_of_block": dupe.get("duplicate_of_block"),
                    "source_overlap": round(similarity["source_overlap"], 4),
                    "candidate_overlap": round(similarity["candidate_overlap"], 4),
                    "overview_similarity": round(similarity["overview_similarity"], 4),
                    "capability_similarity": round(similarity["capability_similarity"], 4),
                }
            )
    return duplicates


def stage_matched_outputs(
    blocks: list[ParsedContrastiveBlock],
    manifest: list[dict[str, Any]],
    *,
    staged_root: Path = DEFAULT_STAGED_ROOT,
) -> list[str]:
    block_by_index = {block.block_index: block for block in blocks}
    staged_paths: list[str] = []

    for entry in manifest:
        if entry.get("status") != "matched":
            continue
        flow_id = entry.get("matched_flow_id")
        if not flow_id:
            continue

        block = block_by_index[int(entry["block_index"])]
        stage_dir = staged_root / str(flow_id)
        stage_path = stage_dir / "contrastive_candidate_requirements.json"
        payload = {
            "matched_flow_id": flow_id,
            "source_block_index": block.block_index,
            "flow_overview": block.flow_overview,
            "capability_summary": block.capability_summary,
            "requirements": block.requirements,
            "match_score": entry.get("score"),
            "match_reasons": entry.get("match_reasons", []),
            "duplicate_status": entry.get("status"),
        }

        if stage_path.exists():
            existing = json.loads(stage_path.read_text(encoding="utf-8"))
            if existing.get("source_block_index") != block.block_index:
                raise ValueError(
                    f"Conflicting staged contrastive import for {flow_id}: "
                    f"{existing.get('source_block_index')} vs {block.block_index}"
                )
        write_json(stage_path, payload)
        staged_paths.append(str(stage_path))

    return staged_paths


def build_unmatched_expected_flows(catalog: list[dict[str, Any]], manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matched_flow_ids = {
        str(entry["matched_flow_id"])
        for entry in manifest
        if entry.get("status") == "matched" and entry.get("matched_flow_id")
    }
    unmatched: list[dict[str, Any]] = []
    for flow in catalog:
        flow_id = str(flow["flow_id"])
        if flow_id in matched_flow_ids:
            continue
        unmatched.append(
            {
                "flow_id": flow_id,
                "website": flow.get("website"),
                "task_description": flow.get("task_description"),
            }
        )
    return unmatched


def build_import_report(
    *,
    blocks: list[ParsedContrastiveBlock],
    manifest: list[dict[str, Any]],
    duplicates: list[dict[str, Any]],
    unmatched_expected_flows: list[dict[str, Any]],
) -> str:
    matched = [entry for entry in manifest if entry.get("status") == "matched"]
    ambiguous = [entry for entry in manifest if entry.get("status") == "ambiguous"]
    duplicate_entries = [entry for entry in manifest if entry.get("status") == "duplicate"]
    unmatched = [entry for entry in manifest if entry.get("status") == "unmatched"]

    lines = [
        "# Contrastive Import Report",
        "",
        f"- Parsed blocks: {len(blocks)}",
        f"- Confidently matched unique flows: {len(matched)}",
        f"- Duplicate blocks: {len(duplicate_entries)}",
        f"- Ambiguous blocks: {len(ambiguous)}",
        f"- Unmatched blocks: {len(unmatched)}",
        f"- Expected flows without a matched block: {len(unmatched_expected_flows)}",
        "",
        "## Matched Blocks",
    ]

    for entry in matched:
        lines.append(
            f"- Block {entry['block_index']} -> {entry['matched_flow_id']} "
            f"(score {entry['score']}, gap {entry['score_gap']})"
        )

    lines.append("")
    lines.append("## Duplicate Blocks")
    if duplicates:
        for item in duplicates:
            lines.append(
                f"- Block {item['duplicate_block_index']} duplicates block {item['kept_block_index']} "
                f"for flow {item['flow_id']}"
            )
    else:
        lines.append("- None")

    lines.append("")
    lines.append("## Ambiguous Blocks")
    if ambiguous:
        for entry in ambiguous:
            lines.append(
                f"- Block {entry['block_index']}: best={entry['matched_flow_id']} "
                f"({entry['score']}), runner_up={entry['runner_up_flow_id']} "
                f"({entry['runner_up_score']}), gap={entry['score_gap']}"
            )
    else:
        lines.append("- None")

    lines.append("")
    lines.append("## Unmatched Expected Flows")
    if unmatched_expected_flows:
        for flow in unmatched_expected_flows:
            lines.append(f"- {flow['flow_id']}: {flow.get('task_description')}")
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"
