import json

import pytest

from ui_verifier.requirements.claim_decomposition import (
    DecompositionLLMError,
    FakeLLMClient,
    RuleGuidedLLMClaimDecomposer,
    decompose_requirement,
    decompose_requirement_with_diagnostics,
    build_requirement_claims,
    decompose_requirement_claim_texts,
)


def test_decompose_requirement_splits_compound_pure_requirement() -> None:
    text = (
        "The tool must provide a capability to manually input and edit fixed data. "
        "Such data includes HVAC unit set points, specifications, and configuration information. "
        "This data must be stored for subsequent use by the diagnostic tool for review and verification "
        "by other users and management. The tool should provide for configuration management of fixed data."
    )

    claims = decompose_requirement_claim_texts(text)

    assert "The tool provides a capability to manually input fixed data." in claims
    assert "The tool provides a capability to manually edit fixed data." in claims
    assert "Such data includes HVAC unit set points, specifications, and configuration information." in claims
    assert "This data is stored for subsequent use by the diagnostic tool for review and verification by other users and management." in claims
    assert "The tool provides for configuration management of fixed data." in claims


def test_decompose_requirement_alias_matches_claim_text_decomposition() -> None:
    text = "The system shall show a confirmation banner and display a total."

    assert decompose_requirement(text) == decompose_requirement_claim_texts(text)


def test_build_requirement_claims_adds_review_metadata() -> None:
    claims = build_requirement_claims(
        "The system shall allow applicants to filter job openings by department.",
        "REQ-01",
    )

    assert claims == [
        {
            "claim_id": "REQ-01-C1",
            "claim": "The system allows applicants to filter job openings by department.",
            "claim_text": "The system allows applicants to filter job openings by department.",
            "claim_kind": "OBSERVABLE_CORE",
            "claim_type": "OBSERVABLE",
            "importance": "CORE",
            "status": "MISSING",
            "source": "requirement_decomposition",
        }
    ]


def test_decompose_requirement_strips_pure_heading_and_splits_options() -> None:
    text = (
        "3.22 Information Clicking on Info brings up a dialog window, on which you can select "
        "the List of packages or Windows Information. The first option opens Terminal and presents "
        "you with a list of packages and libraries installed in GParted."
    )

    claims = decompose_requirement_claim_texts(text)

    assert claims[0] == "Clicking on Info brings up a dialog window, on which you can select the List of packages."
    assert claims[1] == "Clicking on Info brings up a dialog window, on which you can select Windows Information."
    assert "The first option opens Terminal." in claims
    assert "The first option presents users with a list of packages and libraries installed in GParted." in claims


def test_decompose_requirement_splits_retention_purpose_clause() -> None:
    text = (
        "The system shall retain the selected park context in later purchase and checkout screens "
        "so users can verify that they are still completing a pass purchase for the intended park."
    )

    claims = decompose_requirement_claim_texts(text)

    assert "The system retains the selected park context in later purchase screens." in claims
    assert "The system retains the selected park context in checkout screens." in claims
    assert "Users can verify that they are still completing a pass purchase for the intended park." in claims


def test_decompose_requirement_splits_including_list() -> None:
    text = "The system shall present an itemized pre-checkout order summary including subtotal, fees, tax, and total."

    claims = decompose_requirement_claim_texts(text)

    assert "The system presents an itemized pre-checkout order summary." in claims
    assert "The presented itemized pre-checkout order summary includes subtotal." in claims
    assert "The presented itemized pre-checkout order summary includes fees." in claims
    assert "The presented itemized pre-checkout order summary includes tax." in claims
    assert "The presented itemized pre-checkout order summary includes total." in claims


def test_decompose_requirement_splits_without_requiring_clause() -> None:
    text = (
        "The system shall make onboard dining information discoverable through the public site navigation "
        "without requiring the user to enter a booking flow first."
    )

    claims = decompose_requirement_claim_texts(text)

    assert "The system makes onboard dining information discoverable through the public site navigation." in claims
    assert "The user is not required to enter a booking flow first." in claims


def test_decompose_requirement_preserves_disjunctive_handoff_destination() -> None:
    text = (
        "The system shall provide visible confirmation that a selected job posting has been handed off "
        "to the chosen external sharing channel or compose surface."
    )

    claims = decompose_requirement_claim_texts(text)

    assert claims == [
        "The system provides visible confirmation that a selected job posting has been handed off "
        "to the chosen external sharing channel or compose surface."
    ]


def test_rule_based_decomposition_works_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = decompose_requirement_with_diagnostics(
        "The system shall display the checkout total.",
        strategy="rule_based",
    )

    assert result.source == "rule_based"
    assert result.claims[0].claim_text == "The system displays the checkout total."
    assert result.model_name is None


def test_rule_guided_llm_sends_structured_rule_context(tmp_path) -> None:
    text = (
        "The system shall allow public browsing of job listings and posting details, "
        "while requiring applicant authentication before entering the application workflow."
    )
    fake = FakeLLMClient(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_text": "The UI allows public browsing of job listings and posting details.",
                        "claim_kind": "OBSERVABLE_UI",
                        "ui_evaluability": "UI_VERIFIABLE",
                        "importance": "CORE",
                    },
                    {
                        "claim_text": "The system requires applicant authentication before entering the application workflow.",
                        "claim_kind": "MIXED",
                        "ui_evaluability": "PARTIALLY_UI_VERIFIABLE",
                        "importance": "CORE",
                    },
                ],
                "notes": "split visible browsing from authentication",
            }
        )
    )

    result = RuleGuidedLLMClaimDecomposer(fake, cache_dir=tmp_path).decompose(text)

    assert result.source == "rule_guided_llm"
    assert result.prompt_version == "CLAIM_DECOMPOSITION_RULE_GUIDED_V1"
    assert result.model_name == "fake-llm"
    assert "LLM_USED" in result.quality_flags
    prompt = fake.prompts[0]
    assert '"original_text"' in prompt
    assert '"rule_based_claims"' in prompt
    assert '"quality_flags"' in prompt
    assert '"detected_patterns"' in prompt
    assert "WHILE_REQUIRING" in prompt


def test_rule_guided_llm_parses_valid_fake_json(tmp_path) -> None:
    text = (
        "The system shall let users remove individual active search or filter criteria directly "
        "from the results view and immediately refresh the matching job set."
    )
    fake = FakeLLMClient(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_text": "The UI lets users remove individual active search or filter criteria directly from the results view.",
                        "claim_kind": "OBSERVABLE_UI",
                        "ui_evaluability": "UI_VERIFIABLE",
                        "importance": "CORE",
                    },
                    {
                        "claim_text": "The matching job set refreshes after an active search or filter criterion is removed.",
                        "claim_kind": "OBSERVABLE_UI",
                        "ui_evaluability": "UI_VERIFIABLE",
                        "importance": "CORE",
                    },
                ]
            }
        )
    )

    result = RuleGuidedLLMClaimDecomposer(fake, cache_dir=tmp_path).decompose(text)

    assert [claim.claim_text for claim in result.claims] == [
        "The UI lets users remove individual active search or filter criteria directly from the results view.",
        "The matching job set refreshes after an active search or filter criterion is removed.",
    ]
    assert all(claim.claim_kind == "OBSERVABLE_UI" for claim in result.claims)


def test_rule_guided_llm_invalid_json_falls_back_or_raises(tmp_path) -> None:
    text = "The system shall visually confirm when a store has been set as the user's home store and reflect that status in the results view."
    fallback = RuleGuidedLLMClaimDecomposer(
        FakeLLMClient("not json"),
        cache_dir=tmp_path / "fallback",
        use_cache=False,
        strict=False,
    ).decompose(text)

    assert "LLM_PARSE_ERROR" in fallback.quality_flags
    assert fallback.rule_based_claims
    assert [claim.claim_text for claim in fallback.claims] == fallback.rule_based_claims

    with pytest.raises(DecompositionLLMError):
        RuleGuidedLLMClaimDecomposer(
            FakeLLMClient("not json"),
            cache_dir=tmp_path / "strict",
            use_cache=False,
            strict=True,
        ).decompose(text)


def test_rule_guided_llm_can_repair_weak_rule_output(tmp_path) -> None:
    text = (
        "The system shall perform any required financing or approval check before finalizing "
        "a flexible payment agreement and present the resulting status to the user."
    )
    fake = FakeLLMClient(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_text": "The system performs any required financing or approval check before finalizing a flexible payment agreement.",
                        "claim_kind": "HIDDEN_SYSTEM",
                        "ui_evaluability": "NOT_UI_VERIFIABLE",
                        "importance": "CORE",
                    },
                    {
                        "claim_text": "The UI presents the resulting financing or approval status to the user.",
                        "claim_kind": "OBSERVABLE_UI",
                        "ui_evaluability": "UI_VERIFIABLE",
                        "importance": "CORE",
                    },
                ]
            }
        )
    )

    result = RuleGuidedLLMClaimDecomposer(fake, cache_dir=tmp_path).decompose(text)

    assert "HIDDEN_VISIBLE_MIX" in result.quality_flags
    assert "PERFORM_AND_PRESENT" in result.detected_patterns
    assert [claim.claim_kind for claim in result.claims] == ["HIDDEN_SYSTEM", "OBSERVABLE_UI"]


def test_rule_guided_llm_cache_read_write(tmp_path) -> None:
    text = (
        "The system shall show complete store detail coverage for each returned location, "
        "including address, phone contact, and operating hours."
    )
    payload = {
        "claims": [
            {
                "claim_text": "The UI shows address information for each returned location.",
                "claim_kind": "OBSERVABLE_UI",
                "ui_evaluability": "UI_VERIFIABLE",
                "importance": "CORE",
            },
            {
                "claim_text": "The UI shows phone contact information for each returned location.",
                "claim_kind": "OBSERVABLE_UI",
                "ui_evaluability": "UI_VERIFIABLE",
                "importance": "CORE",
            },
            {
                "claim_text": "The UI shows operating hours for each returned location.",
                "claim_kind": "OBSERVABLE_UI",
                "ui_evaluability": "UI_VERIFIABLE",
                "importance": "CORE",
            },
        ]
    }
    first_client = FakeLLMClient(json.dumps(payload))
    first = RuleGuidedLLMClaimDecomposer(first_client, cache_dir=tmp_path).decompose(text)
    second_client = FakeLLMClient([])
    second = RuleGuidedLLMClaimDecomposer(second_client, cache_dir=tmp_path).decompose(text)

    assert first.cache_key == second.cache_key
    assert first.raw_response_path == second.raw_response_path
    assert second_client.prompts == []
    assert len(list(tmp_path.glob("*.json"))) == 1
