from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ui_verifier.localization import TextBoxLocalizer
from ui_verifier.verification_pipeline.claim_verification import ClaimVerifier
from ui_verifier.verification_pipeline.evidence_retrieval import EvidenceRetriever, LexicalEvidenceRetriever
from ui_verifier.verification_pipeline.label_aggregation import LabelAggregator
from ui_verifier.verification_pipeline.requirement_understanding import RequirementUnderstanding
from ui_verifier.verification_pipeline.schemas import ClaimVerificationResult, EvidenceItem, PipelineInput, PipelineOutput
from ui_verifier.verification_pipeline.screen_understanding import ScreenUnderstanding


@runtime_checkable
class BatchClaimVerifier(Protocol):
    def verify_many(self, jobs: list[tuple]) -> list[ClaimVerificationResult]:
        ...


class EvidenceFirstVerificationPipeline:
    def __init__(
        self,
        *,
        screen_understander: ScreenUnderstanding | None = None,
        requirement_understander: RequirementUnderstanding | None = None,
        evidence_retriever: EvidenceRetriever | None = None,
        claim_verifier: ClaimVerifier | None = None,
        label_aggregator: LabelAggregator | None = None,
        evidence_localizer: TextBoxLocalizer | None = None,
        max_claim_workers: int = 1,
    ) -> None:
        if max_claim_workers < 1:
            raise ValueError("max_claim_workers must be at least 1")
        self.screen_understander = screen_understander or ScreenUnderstanding()
        self.requirement_understander = requirement_understander or RequirementUnderstanding()
        self.evidence_retriever = evidence_retriever or LexicalEvidenceRetriever()
        self.claim_verifier = claim_verifier or ClaimVerifier()
        self.label_aggregator = label_aggregator or LabelAggregator()
        self.evidence_localizer = evidence_localizer or TextBoxLocalizer()
        self.max_claim_workers = max_claim_workers

    def run(self, pipeline_input: PipelineInput) -> PipelineOutput:
        screens = self.screen_understander.understand(pipeline_input.screenshots)
        requirement_understandings = self.requirement_understander.understand_many(pipeline_input.requirements)
        all_claims = [
            claim
            for requirement_understanding in requirement_understandings
            for claim in requirement_understanding.claims
        ]
        candidate_evidence = self.evidence_retriever.retrieve(all_claims, screens)
        verification_jobs = []

        for requirement_understanding in requirement_understandings:
            verification_jobs.extend(
                (
                    claim,
                    candidate_evidence.get(claim.claim_id, []),
                    requirement_understanding.ui_evaluability,
                )
                for claim in requirement_understanding.claims
            )

        if isinstance(self.claim_verifier, BatchClaimVerifier):
            verified_claims = self.claim_verifier.verify_many(verification_jobs)
        elif self.max_claim_workers == 1:
            verified_claims = [self._verify_claim(job) for job in verification_jobs]
        else:
            with ThreadPoolExecutor(
                max_workers=self.max_claim_workers,
                thread_name_prefix="claim-verifier",
            ) as executor:
                verified_claims = list(executor.map(self._verify_claim, verification_jobs))

        verified_claims = [
            self._localize_claim_evidence(result) if isinstance(result, ClaimVerificationResult) else result
            for result in verified_claims
        ]

        results = []
        claim_offset = 0
        for requirement_understanding in requirement_understandings:
            claim_count = len(requirement_understanding.claims)
            claim_results = verified_claims[claim_offset : claim_offset + claim_count]
            claim_offset += claim_count
            result = self.label_aggregator.aggregate(
                requirement=requirement_understanding.requirement,
                ui_evaluability=requirement_understanding.ui_evaluability,
                claim_results=claim_results,
                requirement_uncertainty_reasons=requirement_understanding.uncertainty_reasons,
                screens_available=bool(screens),
                metadata={
                    "requirement_understanding_rationale": requirement_understanding.rationale,
                    "decomposition_source": requirement_understanding.decomposition_source,
                },
            )
            results.append(result)

        return PipelineOutput(
            flow_id=pipeline_input.flow_id,
            screen_representations=screens,
            results=results,
            metadata={
                **pipeline_input.metadata,
                "pipeline": "evidence_first_verification_pipeline",
                "retriever": self.evidence_retriever.__class__.__name__,
                "retrieval_batch_claims": len(all_claims),
                "max_claim_workers": self.max_claim_workers,
            },
        )

    def _verify_claim(self, job: tuple) -> object:
        claim, evidence, ui_evaluability = job
        result = self.claim_verifier.verify(
            claim,
            evidence,
            ui_evaluability=ui_evaluability,
        )
        if isinstance(result, ClaimVerificationResult):
            return self._localize_claim_evidence(result)
        return result

    def _localize_claim_evidence(self, result: ClaimVerificationResult) -> ClaimVerificationResult:
        localized_evidence = [
            self._localize_evidence_item(result.claim_text, item)
            for item in result.evidence
        ]
        if localized_evidence == result.evidence:
            return result
        return result.model_copy(update={"evidence": localized_evidence})

    def _localize_evidence_item(self, claim_text: str, item: EvidenceItem) -> EvidenceItem:
        if item.bbox:
            return item
        # Gemini now grounds its own semantic evidence regions in the same call
        # that decides the claim. A missing model region is preferable to a
        # semantically unrelated OCR keyword box. OCR localization remains the
        # deterministic fallback for non-visual verifiers and legacy evidence.
        if item.source == "gemini_image":
            return item
        query_source = "claim_text"
        suggestions = self.evidence_localizer.suggest(claim_text, Path(item.screenshot_path), max_candidates=1)
        if not suggestions and item.visible_observation.strip():
            query_source = "visible_observation"
            suggestions = self.evidence_localizer.suggest(
                item.visible_observation,
                Path(item.screenshot_path),
                max_candidates=1,
            )
        if not suggestions:
            return item
        suggestion = suggestions[0]
        bbox = suggestion.get("bbox")
        if not isinstance(bbox, dict):
            return item
        metadata: dict[str, Any] = {
            **item.metadata,
            "bbox_localization": {
                "source": suggestion.get("source"),
                "level": suggestion.get("level"),
                "score": suggestion.get("score"),
                "matched_text": suggestion.get("matched_text"),
                "image_path": suggestion.get("image_path"),
                "image_width": suggestion.get("image_width"),
                "image_height": suggestion.get("image_height"),
                "coordinate_space": suggestion.get("coordinate_space"),
                "query_source": query_source,
            },
        }
        bbox_metadata: dict[str, Any] = {
            "image_path": suggestion.get("image_path"),
            "image_width": suggestion.get("image_width"),
            "image_height": suggestion.get("image_height"),
            "coordinate_space": suggestion.get("coordinate_space"),
            "source": suggestion.get("source"),
            "confidence": suggestion.get("confidence"),
            "matched_text": suggestion.get("matched_text"),
            "score": suggestion.get("score"),
            "level": suggestion.get("level"),
            "query_source": query_source,
        }
        return item.model_copy(
            update={
                "bbox": [bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]],
                "bbox_metadata": bbox_metadata,
                "metadata": metadata,
            }
        )
