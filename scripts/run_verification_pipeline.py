from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is optional for CLI use.
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui_verifier.common.flow_utils import find_step_images, parse_step_number
from ui_verifier.model_config import model_name_for, provider_for, temperature_for
from ui_verifier.common.json_utils import load_json
from ui_verifier.verification_pipeline.batched_gemini_image_claim_verifier import BatchedGeminiImageClaimVerifier
from ui_verifier.verification_pipeline.claim_verification import ClaimVerifier
from ui_verifier.verification_pipeline.evidence_retrieval import build_evidence_retriever
from ui_verifier.verification_pipeline.gemini_image_claim_verifier import GeminiImageClaimVerifier
from ui_verifier.verification_pipeline.pipeline import EvidenceFirstVerificationPipeline
from ui_verifier.verification_pipeline.requirement_understanding import GeminiClaimDecomposer, RequirementUnderstanding
from ui_verifier.verification_pipeline.schemas import PipelineInput, RequirementInput, ScreenshotStep


def _load_steps_metadata(flow_dir: Path) -> dict[int, dict[str, Any]]:
    steps_path = flow_dir / "steps.json"
    if not steps_path.exists():
        return {}

    data = load_json(steps_path)
    if not isinstance(data, list):
        return {}

    by_index: dict[int, dict[str, Any]] = {}
    for offset, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue
        try:
            step_index = int(item.get("step_index", offset))
        except (TypeError, ValueError):
            step_index = offset
        metadata: dict[str, Any] = {}
        for key in ("raw_html", "action_uid", "url", "operation", "pos_candidates"):
            if key in item:
                metadata[key] = item[key]
        by_index[step_index] = metadata
    return by_index


def _preferred_screenshot_path(flow_dir: Path, path: Path) -> Path:
    candidates = [
        flow_dir / "original" / path.name,
        flow_dir / "originals" / path.name,
        flow_dir / "full" / path.name,
        flow_dir / "fullres" / path.name,
        flow_dir / "hires" / path.name,
    ]
    existing = [candidate for candidate in candidates if candidate.is_file()]
    if not existing:
        return path
    try:
        from PIL import Image

        def pixel_count(candidate: Path) -> int:
            with Image.open(candidate) as image:
                return int(image.width) * int(image.height)

        return max([path, *existing], key=pixel_count)
    except Exception:
        return path


def discover_screenshot_steps(flow_dir: Path, *, image_variant: str = "processed") -> list[ScreenshotStep]:
    metadata_by_step = _load_steps_metadata(flow_dir)
    paths = sorted(find_step_images(flow_dir), key=parse_step_number)
    return [
        ScreenshotStep(
            step_index=parse_step_number(path),
            screenshot_path=str(
                _preferred_screenshot_path(flow_dir, path)
                if image_variant == "preferred-original"
                else path
            ),
            metadata=metadata_by_step.get(parse_step_number(path), {}),
        )
        for path in paths
    ]


def _requirement_items(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("requirements", "items", "verdicts"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return [data]
    raise ValueError("requirements JSON must be an object or a list")


def _requirement_text(item: dict[str, Any]) -> str:
    for key in ("text", "requirement_text", "harvested_text", "claim_text"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise ValueError(f"Could not find requirement text in item keys: {sorted(item)}")


def _provided_claim_texts(item: dict[str, Any]) -> list[str]:
    """Return only frozen claim wording, excluding annotation labels/evidence."""
    claims = item.get("claims")
    if not isinstance(claims, list):
        return []

    texts: list[str] = []
    for claim in claims:
        if isinstance(claim, str):
            text = claim.strip()
        elif isinstance(claim, dict):
            value = claim.get("claim_text") or claim.get("claim") or claim.get("text")
            text = value.strip() if isinstance(value, str) else ""
        else:
            text = ""
        if text and text not in texts:
            texts.append(text)
    return texts


def load_requirements(path: Path, *, default_flow_id: str) -> list[RequirementInput]:
    data = load_json(path)
    requirements: list[RequirementInput] = []
    for index, item in enumerate(_requirement_items(data), start=1):
        if isinstance(item, str):
            requirements.append(
                RequirementInput(
                    requirement_id=f"REQ-{index:03d}",
                    text=item,
                    flow_id=default_flow_id,
                    metadata={"source_path": str(path)},
                )
            )
            continue
        if not isinstance(item, dict):
            raise ValueError("Each requirement item must be a string or object")

        requirement_id = (
            item.get("requirement_id")
            or item.get("id")
            or item.get("harvest_id")
            or item.get("claim_id")
            or f"REQ-{index:03d}"
        )
        requirements.append(
            RequirementInput(
                requirement_id=str(requirement_id),
                text=_requirement_text(item),
                flow_id=str(item.get("flow_id") or default_flow_id),
                metadata={
                    "provided_claim_texts": _provided_claim_texts(item),
                    "source_path": str(path),
                    "source_record_keys": sorted(str(key) for key in item),
                },
            )
        )
    return requirements


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the evidence-first UI verification pipeline.")
    parser.add_argument("--flow-dir", type=Path, required=True, help="Directory containing ordered step_XX.png files")
    parser.add_argument(
        "--image-variant",
        choices=["processed", "preferred-original"],
        default="processed",
        help="Use processed step images or the largest available original/high-resolution counterpart.",
    )
    parser.add_argument("--requirements", type=Path, required=True, help="JSON requirements file")
    parser.add_argument(
        "--requirements-source",
        choices=["accepted", "benchmark", "custom"],
        default="custom",
        help="Semantic source of the requirements file. Use benchmark for verification_gold inputs.",
    )
    parser.add_argument("--out", type=Path, required=True, help="Output JSON path")
    parser.add_argument("--retriever", choices=["lexical", "tfidf", "embedding", "llm"], default="lexical")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--claims",
        dest="claims_enabled",
        action="store_true",
        default=True,
        help="Decompose requirements into independently verified claims. Enabled by default.",
    )
    parser.add_argument(
        "--no-claims",
        dest="claims_enabled",
        action="store_false",
        help="Disable claim decomposition and verify each complete requirement as one unit.",
    )
    parser.add_argument(
        "--llm-claim-fallback",
        dest="llm_claim_fallback",
        action="store_true",
        default=True,
        help="Use one lightweight Gemini call to decompose requirements where heuristic decomposition looks weak. Enabled by default.",
    )
    parser.add_argument(
        "--no-llm-claim-fallback",
        dest="llm_claim_fallback",
        action="store_false",
        help="Use only deterministic rule-based claim decomposition.",
    )
    parser.add_argument("--claim-model", type=str, default=model_name_for("claim_decomposition"))
    parser.add_argument("--claim-provider", choices=["gemini", "deepseek"], default=provider_for("claim_decomposition"))
    parser.add_argument("--retriever-model", type=str, default=model_name_for("evidence_retrieval"))
    parser.add_argument("--retriever-provider", choices=["gemini", "deepseek"], default=provider_for("evidence_retrieval"))
    parser.add_argument("--retriever-temperature", type=float, default=temperature_for("evidence_retrieval"))
    parser.add_argument(
        "--embedding-model-path",
        type=str,
        default=None,
        help="Optional local sentence-transformers model path. No download is attempted.",
    )
    parser.add_argument("--verifier", choices=["deterministic", "gemini-image"], default="deterministic")
    parser.add_argument(
        "--execution-mode",
        choices=["per-claim", "batched-topk", "single-call"],
        default="batched-topk",
        help="Verifier orchestration mode. batched-topk and single-call apply to gemini-image verification.",
    )
    parser.add_argument("--verifier-model", type=str, default=model_name_for("demo_image_verifier"))
    parser.add_argument("--verifier-temperature", type=float, default=temperature_for("demo_image_verifier"))
    parser.add_argument("--verifier-thinking-level", choices=["minimal", "low", "medium", "high"])
    parser.add_argument(
        "--verifier-thinking-budget",
        type=int,
        default=None,
        help="Gemini 2.5 thinking token budget; use 0 to disable. Mutually exclusive with thinking level.",
    )
    parser.add_argument("--verifier-max-output-tokens", type=int, default=None)
    parser.add_argument("--grounding-candidates", type=Path, default=None)
    parser.add_argument("--grounding-assets-dir", type=Path, default=None)
    parser.add_argument(
        "--verifier-predict-ui-evaluability",
        action="store_true",
        help="Hide the pipeline UI-evaluability label and ask the visual verifier to predict it jointly.",
    )
    parser.add_argument("--max-verifier-images", type=int, default=6)
    parser.add_argument(
        "--max-verifier-group-images",
        type=int,
        default=-1,
        help="Maximum images attached per batched prompt. Use -1 for no group cap.",
    )
    parser.add_argument(
        "--max-verifier-group-claims",
        type=int,
        default=-1,
        help="Maximum claims per batched verification prompt. Use -1 for no group cap.",
    )
    parser.add_argument(
        "--no-sequence-context",
        action="store_true",
        help="Do not automatically add first/last screenshots for sequence-like claims. Useful for staged grouping ablations.",
    )
    parser.add_argument(
        "--verifier-chronology-mode",
        choices=["chronological", "destroyed"],
        default="chronological",
        help=(
            "Use destroyed only for the controlled order ablation: images are deterministically permuted, "
            "original step identities are hidden from the model, and evidence IDs are mapped back after inference."
        ),
    )
    parser.add_argument(
        "--verifier-order-seed",
        type=int,
        default=20260726,
        help="Stable seed used to derive the per-flow permutation for destroyed chronology.",
    )
    parser.add_argument("--gemini-max-retries", type=int, default=0)
    parser.add_argument("--max-gemini-api-calls", type=int, default=10, help="Use -1 for no cap.")
    parser.add_argument(
        "--claim-workers",
        type=int,
        default=4,
        help="Maximum number of independent claim-verification calls to run concurrently.",
    )
    parser.add_argument(
        "--claim-decomposition-policy",
        choices=["disabled", "gated", "always", "provided"],
        default="gated",
        help=(
            "Use disabled for original requirements, gated for conservative splitting, always for legacy eager "
            "splitting, or provided for frozen claims from the requirements file."
        ),
    )
    parser.add_argument("--max-claims", type=int, default=4, help="Maximum claims retained per requirement.")
    parser.add_argument("--verifier-cache", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    if load_dotenv is not None:
        load_dotenv(BASE_DIR / ".env")

    args = parse_args()
    if args.verifier_thinking_level is not None and args.verifier_thinking_budget is not None:
        raise ValueError("--verifier-thinking-level and --verifier-thinking-budget are mutually exclusive")
    if args.verifier_chronology_mode != "chronological" and args.execution_mode == "per-claim":
        raise ValueError("Destroyed chronology currently requires batched-topk or single-call execution.")
    screenshots = discover_screenshot_steps(args.flow_dir, image_variant=args.image_variant)
    if not screenshots:
        raise ValueError(f"No step_*.png screenshots found in {args.flow_dir}")

    requirements = load_requirements(args.requirements, default_flow_id=args.flow_dir.name)
    retriever = build_evidence_retriever(
        args.retriever,
        top_k=args.top_k,
        embedding_model_path=args.embedding_model_path,
        llm_provider=args.retriever_provider,
        llm_model_name=args.retriever_model,
        llm_temperature=args.retriever_temperature,
    )
    fallback_decomposer = (
        GeminiClaimDecomposer(provider=args.claim_provider, model_name=args.claim_model)
        if args.claims_enabled and args.llm_claim_fallback
        else None
    )
    requirement_understander = RequirementUnderstanding(
        max_claims=args.max_claims,
        fallback_decomposer=fallback_decomposer,
        decompose_claims=args.claims_enabled,
        decomposition_policy=args.claim_decomposition_policy if args.claims_enabled else "disabled",
    )
    if args.verifier == "gemini-image":
        cache_path = args.verifier_cache or (
            BASE_DIR
            / "data"
            / "generated"
            / "verification_pipeline_cache"
            / f"{args.flow_dir.name}_{args.execution_mode}_gemini_image_claims.json"
        )
        verifier_kwargs = {
            "flow_id": args.flow_dir.name,
            "screenshot_steps": screenshots,
            "cache_path": cache_path,
            "model_name": args.verifier_model,
            "temperature": args.verifier_temperature,
            "max_images_per_claim": args.max_verifier_images,
            "max_retries": args.gemini_max_retries,
            "max_api_calls": None if args.max_gemini_api_calls < 0 else args.max_gemini_api_calls,
            "include_sequence_context": not args.no_sequence_context,
            "thinking_level": args.verifier_thinking_level,
            "thinking_budget": args.verifier_thinking_budget,
            "max_output_tokens": args.verifier_max_output_tokens,
        }
        if args.execution_mode == "per-claim":
            claim_verifier = GeminiImageClaimVerifier(**verifier_kwargs)
        else:
            claim_verifier = BatchedGeminiImageClaimVerifier(
                **verifier_kwargs,
                grouping_strategy=args.execution_mode,
                max_images_per_group=None if args.max_verifier_group_images < 0 else args.max_verifier_group_images,
                max_claims_per_group=None if args.max_verifier_group_claims < 0 else args.max_verifier_group_claims,
                group_workers=args.claim_workers,
                candidate_package=args.grounding_candidates,
                marked_assets_dir=args.grounding_assets_dir,
                predict_ui_evaluability=args.verifier_predict_ui_evaluability,
                chronology_mode=args.verifier_chronology_mode,
                order_seed=args.verifier_order_seed,
            )
    else:
        claim_verifier = ClaimVerifier()

    pipeline = EvidenceFirstVerificationPipeline(
        requirement_understander=requirement_understander,
        evidence_retriever=retriever,
        claim_verifier=claim_verifier,
        max_claim_workers=args.claim_workers,
    )
    output = pipeline.run(
        PipelineInput(
            flow_id=args.flow_dir.name,
            screenshots=screenshots,
            requirements=requirements,
            metadata={
                "flow_dir": str(args.flow_dir),
                "requirements_path": str(args.requirements),
                "requirements_source": args.requirements_source,
                "requested_retriever": args.retriever,
                "retriever_provider": args.retriever_provider if args.retriever == "llm" else None,
                "retriever_model": args.retriever_model if args.retriever == "llm" else None,
                "top_k": args.top_k,
                "claims_enabled": args.claims_enabled,
                "claim_decomposition_policy": args.claim_decomposition_policy if args.claims_enabled else "disabled",
                "max_claims": args.max_claims,
                "llm_claim_fallback": args.claims_enabled and args.llm_claim_fallback,
                "claim_provider": args.claim_provider,
                "claim_model": args.claim_model if args.claims_enabled and args.llm_claim_fallback else None,
                "verifier": args.verifier,
                "execution_mode": args.execution_mode if args.verifier == "gemini-image" else "per-claim",
                "verifier_model": args.verifier_model if args.verifier == "gemini-image" else None,
                "max_verifier_images": args.max_verifier_images,
                "max_verifier_group_images": args.max_verifier_group_images if args.verifier == "gemini-image" else None,
                "max_verifier_group_claims": args.max_verifier_group_claims if args.verifier == "gemini-image" else None,
                "include_sequence_context": not args.no_sequence_context if args.verifier == "gemini-image" else None,
                "claim_workers": args.claim_workers,
                "verifier_thinking_level": args.verifier_thinking_level,
                "verifier_thinking_budget": args.verifier_thinking_budget,
                "verifier_max_output_tokens": args.verifier_max_output_tokens,
                "grounding_candidates": str(args.grounding_candidates) if args.grounding_candidates else None,
                "grounding_assets_dir": str(args.grounding_assets_dir) if args.grounding_assets_dir else None,
                "verifier_predict_ui_evaluability": args.verifier_predict_ui_evaluability,
                "verifier_chronology_mode": (
                    args.verifier_chronology_mode if args.verifier == "gemini-image" else None
                ),
                "verifier_order_seed": (
                    args.verifier_order_seed if args.verifier == "gemini-image" else None
                ),
            },
        )
    )
    if isinstance(claim_verifier, GeminiImageClaimVerifier):
        diagnostics = dict(claim_verifier.diagnostics)
        output.metadata["gemini_image_verifier"] = diagnostics
        output.metadata["gemini_mllm_verifier_used"] = (
            int(diagnostics.get("api_calls", 0)) + int(diagnostics.get("cache_hits", 0))
        ) > 0
        output.metadata["gemini_mllm_verifier_fallback_used"] = int(diagnostics.get("fallbacks", 0)) > 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(output.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"flow={output.flow_id} requirements={len(output.results)} out={args.out}")
    for result in output.results:
        statuses = {}
        for claim in result.claims:
            statuses[claim.status.value] = statuses.get(claim.status.value, 0) + 1
        evidence_steps = sorted({item.step_index for item in result.evidence})
        print(
            f"{result.requirement_id}: label={result.final_label.value} "
            f"claims={statuses} evidence_steps={evidence_steps}"
        )


if __name__ == "__main__":
    main()
