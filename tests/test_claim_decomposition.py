from ui_verifier.requirements.claim_decomposition import (
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
