from __future__ import annotations

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
    ) -> None:
        self.screen_understander = screen_understander or ScreenUnderstanding()
        self.requirement_understander = requirement_understander or RequirementUnderstanding()
        self.evidence_retriever = evidence_retriever or LexicalEvidenceRetriever()
        self.claim_verifier = claim_verifier or ClaimVerifier()
        self.label_aggregator = label_aggregator or LabelAggregator()

    def run(self, pipeline_input: PipelineInput) -> PipelineOutput:
        screens = self.screen_understander.understand(pipeline_input.screenshots)
        results = []
        requirement_understandings = self.requirement_understander.understand_many(pipeline_input.requirements)

        for requirement_understanding in requirement_understandings:
            requirement = requirement_understanding.requirement
            candidate_evidence = self.evidence_retriever.retrieve(
                requirement_understanding.claims,
                screens,
            )
            claim_results = [
                self.claim_verifier.verify(
                    claim,
                    candidate_evidence.get(claim.claim_id, []),
                    ui_evaluability=requirement_understanding.ui_evaluability,
                )
                for claim in requirement_understanding.claims
            ]
            result = self.label_aggregator.aggregate(
                requirement=requirement,
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
            },
        )
