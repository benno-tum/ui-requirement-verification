from __future__ import annotations

from ui_verifier.requirements.contrastive_import import (
    ParsedContrastiveBlock,
    create_match_manifest,
    parse_concatenated_json_blocks,
)


def _flow(flow_id: str, website: str, task: str, gold_texts: list[tuple[str, str]]) -> dict:
    return {
        "flow_id": flow_id,
        "website": website,
        "domain": "web",
        "task_description": task,
        "gold_requirements": [
            {"requirement_id": req_id, "text": text}
            for req_id, text in gold_texts
        ],
        "harvested_requirements": [],
        "candidate_requirements": [],
        "flow_overview": None,
        "capability_summary": [],
        "flow_dir": f"/tmp/{flow_id}",
        "_normalized_gold_texts": {
            text.lower(): req_id for req_id, text in gold_texts
        },
    }


def test_parse_concatenated_json_blocks_skips_interstitial_text() -> None:
    raw = """
{"flow_overview":"one","capability_summary":[],"requirements":[]}
those are def not in order:
{"flow_overview":"two","capability_summary":[],"requirements":[]}
""".strip()

    blocks = parse_concatenated_json_blocks(raw)

    assert len(blocks) == 2
    assert blocks[0].flow_overview == "one"
    assert blocks[1].flow_overview == "two"
    assert blocks[0].raw_start_offset < blocks[0].raw_end_offset
    assert blocks[1].raw_start_offset < blocks[1].raw_end_offset


def test_create_match_manifest_prefers_gold_text_over_same_website() -> None:
    catalog = [
        _flow(
            "01_sixflags_a",
            "sixflags",
            "Apply for a park role",
            [("REQ-04", "The system shall carry the selected park context into subsequent recruiting screens and park-specific job content.")],
        ),
        _flow(
            "10_sixflags_b",
            "sixflags",
            "Buy tickets and add-ons",
            [("REQ-14", "The system shall preserve the selected park context consistently across discovery, add-on selection, and cart review screens.")],
        ),
    ]
    block = ParsedContrastiveBlock(
        block_index=1,
        flow_overview="Six Flags recruiting flow",
        capability_summary=["Job discovery"],
        requirements=[
            {
                "candidate_text": "The system shall keep the selected park context attached when an applicant proceeds into application start.",
                "source_gold_text": "The system shall carry the selected park context into subsequent recruiting screens and park-specific job content.",
            }
        ],
        raw_start_offset=0,
        raw_end_offset=10,
    )

    manifest = create_match_manifest([block], catalog)

    assert manifest[0]["status"] == "matched"
    assert manifest[0]["matched_flow_id"] == "01_sixflags_a"


def test_create_match_manifest_marks_duplicate_when_same_flow_repeats() -> None:
    catalog = [
        _flow(
            "09_amc",
            "amctheatres",
            "Check a gift card balance",
            [
                ("REQ-05", "The system shall allow an authenticated user to optionally associate a gift card with their account during the balance check process."),
                ("REQ-09", "The system shall return the remaining gift card balance after the user provides valid card credentials."),
            ],
        ),
        _flow(
            "02_gamestop",
            "gamestop",
            "Find the closest store",
            [("REQ-05", "The system shall provide a mechanism for users to select and designate a specific store as their preferred 'home store'.")],
        ),
    ]
    blocks = [
        ParsedContrastiveBlock(
            block_index=1,
            flow_overview="AMC gift card flow",
            capability_summary=["Gift card hub"],
            requirements=[
                {
                    "candidate_text": "The system shall preserve a user's decision to associate a gift card with their account through the remainder of the balance inquiry workflow.",
                    "source_gold_text": "The system shall allow an authenticated user to optionally associate a gift card with their account during the balance check process.",
                },
                {
                    "candidate_text": "The system shall provide an explicit balance inquiry result state.",
                    "source_gold_text": "The system shall return the remaining gift card balance after the user provides valid card credentials.",
                },
            ],
            raw_start_offset=0,
            raw_end_offset=100,
        ),
        ParsedContrastiveBlock(
            block_index=2,
            flow_overview="AMC gift card service area",
            capability_summary=["Gift card hub"],
            requirements=[
                {
                    "candidate_text": "The system shall remember gift cards that a signed in user chooses to associate with their account and make them available again on later visits.",
                    "source_gold_text": "The system shall allow an authenticated user to optionally associate a gift card with their account during the balance check process.",
                },
                {
                    "candidate_text": "The system shall provide an explicit review or result state after balance lookup.",
                    "source_gold_text": "The system shall return the remaining gift card balance after the user provides valid card credentials.",
                },
            ],
            raw_start_offset=101,
            raw_end_offset=200,
        ),
    ]

    manifest = create_match_manifest(blocks, catalog)

    statuses = {entry["block_index"]: entry["status"] for entry in manifest}
    assert statuses[1] == "matched"
    assert statuses[2] == "duplicate"
    assert manifest[1]["duplicate_of_block"] == 1
