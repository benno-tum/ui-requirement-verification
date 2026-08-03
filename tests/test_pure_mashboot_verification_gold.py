import json
from pathlib import Path

from ui_verifier.verification.label_validation import validate_verification_gold_item
from ui_verifier.verification.schemas import VerificationGoldFile, VerificationGoldItem

from scripts.build_pure_mashboot_verification_gold import preserve_accepted_review


def test_mashboot_draft_gold_is_complete_and_valid() -> None:
    path = Path("data/annotations/verification_gold/pure_2010_mashboot/verification_gold.json")
    gold = VerificationGoldFile.load(path)

    assert len(gold.items) == 11
    assert len({item.requirement_id for item in gold.items}) == 11
    assert sum(len(item.claims) for item in gold.items) == 42
    assert all(item.review_status in {"needs_review", "accepted"} for item in gold.items)
    assert next(item for item in gold.items if item.requirement_id == "PURE-MB-CAMPAIGN-001").review_status == "accepted"
    assert all(not validate_verification_gold_item(item).errors for item in gold.items)
    assert all(set(item.evidence_steps).issubset({1, 2, 3}) for item in gold.items)


def test_mashboot_content_claims_cover_the_complete_requirement_not_only_supported_evidence() -> None:
    path = Path("data/annotations/verification_gold/pure_2010_mashboot/verification_gold.json")
    gold = VerificationGoldFile.load(path)
    item = next(item for item in gold.items if item.requirement_id == "PURE-MB-CONTENT-001")

    assert [(claim.claim, claim.status.value) for claim in item.claims] == [
        ("Campaign content supports text.", "SUPPORTED_WITH_CAVEAT"),
        ("Campaign content supports images.", "SUPPORTED"),
        ("Campaign content supports audio.", "MISSING"),
        ("Campaign content supports video.", "SUPPORTED"),
    ]
    assert all(claim.note is None for claim in item.claims)


def test_mashboot_gold_preserves_every_candidate_claim_regardless_of_manual_status() -> None:
    gold = VerificationGoldFile.load(
        Path("data/annotations/verification_gold/pure_2010_mashboot/verification_gold.json")
    )
    candidates = json.loads(
        Path("data/annotations/requirements_candidate/pure_2010_mashboot/candidate_requirements.json").read_text(
            encoding="utf-8"
        )
    )
    gold_by_id = {item.requirement_id: item for item in gold.items}

    for candidate in candidates["requirements"]:
        assert [claim.claim for claim in gold_by_id[candidate["requirement_id"]].claims] == [
            claim["claim_text"] for claim in candidate["claims"]
        ]


def test_create_content_requirement_retains_the_complete_document_interaction_context() -> None:
    gold = VerificationGoldFile.load(
        Path("data/annotations/verification_gold/pure_2010_mashboot/verification_gold.json")
    )
    item = next(item for item in gold.items if item.requirement_id == "PURE-MB-CREATE-002")

    assert [claim.claim for claim in item.claims] == [
        "The Create view provides an Add Content action.",
        "In the Create view, invoking Add Content prompts the user to select a content type.",
        "In the Create view's Add Content prompt, the content-type choices are populated from services the user can access through credentials stored in the system.",
        "In the Create view, selecting a content type creates a section for the selected content type.",
        "In the Create view, the selected content-type section allows the user to add individual content elements.",
        "In the Create view, each content-element row provides a scheduling action.",
        "In the Create view, each content-element row provides an edit action.",
        "In the Create view, each content-element row provides a delete action.",
    ]
    assert all("Create view" in claim.claim for claim in item.claims)
    assert item.claims[2].status.value == "HIDDEN"
    assert all(claim.status.value == "MISSING" for index, claim in enumerate(item.claims) if index != 2)


def test_dashboard_claims_are_conjunctive_subparticles_of_the_requirement() -> None:
    gold = VerificationGoldFile.load(
        Path("data/annotations/verification_gold/pure_2010_mashboot/verification_gold.json")
    )
    item = next(item for item in gold.items if item.requirement_id == "PURE-MB-DASHBOARD-001")

    assert item.text == (
        "The Dashboard shall summarize campaign performance through graphs and metrics including clickthrough "
        "rate, page views, number of comments, and plugin-defined specialized metrics, and shall provide "
        "additional information for the selected metric."
    )
    assert [claim.claim for claim in item.claims] == [
        "The Dashboard summarizes campaign performance through graphs.",
        "The Dashboard includes clickthrough rate as a campaign-performance metric.",
        "The Dashboard includes page views as a campaign-performance metric.",
        "The Dashboard includes number of comments as a campaign-performance metric.",
        "The Dashboard includes plugin-defined specialized campaign-performance metrics.",
        "The Dashboard provides additional information for the selected metric.",
    ]


def test_schedule_default_time_preserves_automatic_system_assignment() -> None:
    gold = VerificationGoldFile.load(
        Path("data/annotations/verification_gold/pure_2010_mashboot/verification_gold.json")
    )
    item = next(item for item in gold.items if item.requirement_id == "PURE-MB-SCHEDULE-001")

    assert item.text == (
        "The Schedule view shall let users drag content from the content bucket to the calendar. Content "
        "dragged to the calendar shall automatically receive a default go-live time of 12am on the selected "
        "day. The Schedule view shall let users select scheduled content and assign a different go-live time."
    )
    assert item.claims[1].claim == (
        "In the Schedule view, content dragged to the calendar automatically receives a default go-live time of 12am on the selected day."
    )


def test_mashboot_builder_preserves_an_accepted_human_review() -> None:
    gold = VerificationGoldFile.load(
        Path("data/annotations/verification_gold/pure_2010_mashboot/verification_gold.json")
    )
    existing = next(item for item in gold.items if item.requirement_id == "PURE-MB-CAMPAIGN-001")
    generated_data = existing.to_dict()
    generated_data.update({"review_status": "needs_review", "annotated_by": "codex_draft"})
    generated = VerificationGoldItem.from_dict(generated_data)

    preserved = preserve_accepted_review(generated, existing)

    assert preserved.review_status == "accepted"
    assert preserved.annotated_by == "benno"


def test_every_open_mashboot_claim_retains_its_requirement_context() -> None:
    gold = VerificationGoldFile.load(
        Path("data/annotations/verification_gold/pure_2010_mashboot/verification_gold.json")
    )
    allowed_prefixes = {
        "PURE-MB-NAV-001": ("The Mashbot web interface",),
        "PURE-MB-DASHBOARD-001": ("The Dashboard",),
        "PURE-MB-DASHBOARD-002": ("The monitoring Dashboard",),
        "PURE-MB-CREATE-002": ("The Create view", "In the Create view"),
        "PURE-MB-SCHEDULE-001": ("In the Schedule view",),
        "PURE-MB-SCHEDULE-002": ("The Schedule-view calendar",),
        "PURE-MB-EXPLORE-001": ("The Explore view",),
        "PURE-MB-SERVICE-001": ("Mashbot",),
    }

    for item in gold.items:
        if item.review_status != "needs_review":
            continue
        assert item.requirement_id in allowed_prefixes
        assert all(claim.claim.startswith(allowed_prefixes[item.requirement_id]) for claim in item.claims)
