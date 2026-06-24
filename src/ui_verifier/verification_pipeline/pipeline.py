from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from ui_verifier.verification_pipeline.claim_verification import ClaimVerifier
from ui_verifier.verification_pipeline.evidence_retrieval import EvidenceRetriever, LexicalEvidenceRetriever
from ui_verifier.verification_pipeline.label_aggregation import LabelAggregator
from ui_verifier.verification_pipeline.requirement_understanding import RequirementUnderstanding
from ui_verifier.verification_pipeline.schemas import PipelineInput, PipelineOutput
from ui_verifier.verification_pipeline.screen_understanding import ScreenUnderstanding


class EvidenceFirstVerificationPipeline:
    def __init__(
        self,
        *,
        screen_understander: ScreenUnderstanding | None = None,
        requirement_understander: RequirementUnderstanding | None = None,
        evidence_retriever: EvidenceRetriever | None = None,
        claim_verifier: ClaimVerifier | None = None,
        label_aggregator: LabelAggregator | None = None,
        max_claim_workers: int = 1,
    ) -> None:
        if max_claim_workers < 1:
            raise ValueError("max_claim_workers must be at least 1")
        self.screen_understander = screen_understander or ScreenUnderstanding()
        self.requirement_understander = requirement_understander or RequirementUnderstanding()
        self.evidence_retriever = evidence_retriever or LexicalEvidenceRetriever()
        self.claim_verifier = claim_verifier or ClaimVerifier()
        self.label_aggregator = label_aggregator or LabelAggregator()
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

        if self.max_claim_workers == 1:
            verified_claims = [self._verify_claim(job) for job in verification_jobs]
        else:
            with ThreadPoolExecutor(
                max_workers=self.max_claim_workers,
                thread_name_prefix="claim-verifier",
            ) as executor:
                verified_claims = list(executor.map(self._verify_claim, verification_jobs))

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
        return self.claim_verifier.verify(
            claim,
            evidence,
            ui_evaluability=ui_evaluability,
        )
