from __future__ import annotations

import json
from pathlib import Path

from ui_verifier.requirements.contrastive_generation import (
    IntendedLabel,
    MutationFamily,
    normalize_model_contrastive_candidates,
    parse_existing_response,
    prepare_manual_bundle,
)
from ui_verifier.requirements.prompting import build_contrastive_from_gold_prompt
from ui_verifier.requirements.schemas import GoldRequirement, GoldRequirementFile, RequirementScope


def _make_gold_file(flow_id: str = "flow-1") -> GoldRequirementFile:
    return GoldRequirementFile(
        dataset="mind2web",
        flow_id=flow_id,
        requirements=[
            GoldRequirement(
                requirement_id="REQ-01",
                flow_id=flow_id,
                text="The system shall let users search for local businesses by service and city.",
                scope=RequirementScope.SINGLE_SCREEN,
                tags=[],
                step_indices=[1],
            ),
            GoldRequirement(
                requirement_id="REQ-02",
                flow_id=flow_id,
                text="The system shall provide autocomplete suggestions while users enter a location.",
                scope=RequirementScope.SINGLE_SCREEN,
                tags=[],
                step_indices=[2],
            ),
        ],
    )


def test_build_contrastive_from_gold_prompt_includes_targets_and_source_material() -> None:
    prompt = build_contrastive_from_gold_prompt(
        task={
            "confirmed_task": "Find coupons for a hair salon in San Diego",
            "website": "Yellow Pages",
            "domain": "local_search",
        },
        gold_payload={
            "flow_overview": "Local business search flow",
            "capability_summary": ["Business search", "Location autocomplete"],
            "accepted_gold_requirements": [{"requirement_id": "REQ-01", "text": "The system shall ..."}],
        },
        target_partially=4,
        target_abstain=3,
        target_not_fulfilled=2,
    )

    assert "Generate additional contrastive candidate requirements" in prompt
    assert "Try to generate:" in prompt
    assert "- 4 items targeting partially_fulfilled" in prompt
    assert "- 3 items targeting abstain" in prompt
    assert "- 2 items targeting not_fulfilled" in prompt
    assert '"accepted_gold_requirements"' in prompt
    assert "Return ONLY valid JSON in this format" in prompt
    assert "missing_visible_step" in prompt
    assert "cross_screen_consistency_extension" in prompt


def test_prepare_manual_bundle_writes_expected_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "contrastive" / "flow-1"
    gold_file = _make_gold_file()
    task = {"confirmed_task": "Find a business", "website": "Yellow Pages", "domain": "local_search"}

    bundle_dir = prepare_manual_bundle(
        output_dir=output_dir,
        prompt="prompt body",
        task=task,
        gold_file=gold_file,
        model_name="manual-chatgpt",
        temperature=0.3,
        target_partially=5,
        target_abstain=4,
        target_not_fulfilled=3,
    )

    assert (bundle_dir / "prompt.txt").read_text(encoding="utf-8") == "prompt body"
    assert json.loads((bundle_dir / "task.json").read_text(encoding="utf-8"))["website"] == "Yellow Pages"
    assert json.loads((bundle_dir / "gold_requirements.json").read_text(encoding="utf-8"))["flow_id"] == "flow-1"
    assert (bundle_dir / "manual_contrastive_raw.txt").exists()
    assert "Re-run the script with `--parse-existing-response`." in (bundle_dir / "README.md").read_text(
        encoding="utf-8"
    )
    context = json.loads((bundle_dir / "generation_context.json").read_text(encoding="utf-8"))
    assert context["model"] == "manual-chatgpt"
    assert context["temperature"] == 0.3


def test_normalize_model_contrastive_filters_duplicates_and_paraphrases(tmp_path: Path) -> None:
    output_dir = tmp_path / "contrastive" / "flow-1"
    output_dir.mkdir(parents=True)
    prompt_path = output_dir / "manual_contrastive_bundle" / "prompt.txt"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("prompt", encoding="utf-8")

    gold_file = _make_gold_file()
    parsed = {
        "flow_overview": "Refined overview",
        "capability_summary": ["Search", "Autocomplete"],
        "requirements": [
            {
                "id": "CONTR-99",
                "candidate_text": "The system shall remember a user's recent service and city search context across later visits.",
                "source_gold_requirement_id": "REQ-01",
                "source_gold_text": "ignored",
                "intended_label": "partially_fulfilled",
                "mutation_family": "persistence_extension",
                "grounding_scope": "INDIRECT_FLOW_GROUNDED",
                "requirement_type": "FR",
                "ui_evaluability": "PARTIALLY_UI_VERIFIABLE",
                "non_evaluable_reason": "BUSINESS_RULE_NOT_VISIBLE",
                "visible_subtype": "STATE_CHANGE_ACROSS_SCREENS",
                "confidence": "HIGH",
                "generation_rationale": "Extends the search feature into remembered context.",
            },
            {
                "candidate_text": "The system shall let users search for local businesses by service and city.",
                "source_gold_requirement_id": "REQ-01",
                "intended_label": "not_fulfilled",
                "mutation_family": "nearby_capability_variant",
                "generation_rationale": "This is too close and should be dropped.",
            },
            {
                "candidate_text": "The system shall remember a user's recent service and city search context across later visits.",
                "source_gold_requirement_id": "REQ-01",
                "intended_label": "abstain",
                "mutation_family": "hidden_state_extension",
                "generation_rationale": "Duplicate text should be dropped.",
            },
            {
                "candidate_text": "The system shall show location suggestions that keep city and nearby neighborhood variants visibly grouped.",
                "source_gold_requirement_id": "REQ-02",
                "intended_label": "not_fulfilled",
                "mutation_family": "stronger_visible_constraint",
                "grounding_scope": "DIRECT_FLOW_GROUNDED",
                "requirement_type": "FR",
                "ui_evaluability": "UI_VERIFIABLE",
                "non_evaluable_reason": "NONE",
                "visible_subtype": "CONTENT_UPDATE",
                "confidence": "MEDIUM",
                "generation_rationale": "Strengthens the visible autocomplete presentation.",
            },
            {
                "candidate_text": "The system shall allow signed-in owners to export their business listings.",
                "source_gold_requirement_id": "",
                "intended_label": "abstain",
                "mutation_family": "policy_or_role_extension",
                "generation_rationale": "Missing source id should be dropped.",
            },
        ],
    }

    contrastive_file = normalize_model_contrastive_candidates(
        parsed=parsed,
        gold_file=gold_file,
        model_name="manual-chatgpt",
        prompt_path=prompt_path,
        output_dir=output_dir,
        generation_temperature=0.2,
        source_flow_overview="Original overview",
        source_capability_summary=["Original capability"],
    )

    assert contrastive_file.flow_overview == "Refined overview"
    assert contrastive_file.capability_summary == ["Search", "Autocomplete"]
    assert len(contrastive_file.requirements) == 2
    assert [req.requirement_id for req in contrastive_file.requirements] == ["CONTR-01", "CONTR-02"]
    assert contrastive_file.requirements[0].mutation_family == MutationFamily.PERSISTENCE_EXTENSION
    assert contrastive_file.requirements[0].intended_label == IntendedLabel.PARTIALLY_FULFILLED
    assert contrastive_file.requirements[0].source_gold_text == gold_file.requirements[0].text
    assert contrastive_file.requirements[1].generation_prompt_path == "manual_contrastive_bundle/prompt.txt"


def test_parse_existing_response_saves_contrastive_candidates(tmp_path: Path) -> None:
    flow_id = "flow-1"
    gold_root = tmp_path / "gold"
    flow_root = tmp_path / "flows"
    context_root = tmp_path / "candidate_context"
    output_root = tmp_path / "contrastive_out"

    gold_dir = gold_root / flow_id
    gold_dir.mkdir(parents=True)
    _make_gold_file(flow_id).save(gold_dir / "gold_requirements.json")

    task_dir = flow_root / flow_id
    task_dir.mkdir(parents=True)
    (task_dir / "task.json").write_text(
        json.dumps(
            {
                "confirmed_task": "Find a local business",
                "website": "Yellow Pages",
                "domain": "local_search",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    context_dir = context_root / flow_id
    context_dir.mkdir(parents=True)
    (context_dir / "harvested_requirements.json").write_text(
        json.dumps(
            {
                "flow_id": flow_id,
                "flow_overview": "Harvested overview",
                "capability_summary": ["Business search", "Location suggestions"],
                "requirements": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    bundle_dir = output_root / flow_id / "manual_contrastive_bundle"
    bundle_dir.mkdir(parents=True)
    raw_response_path = bundle_dir / "manual_contrastive_raw.txt"
    raw_response_path.write_text(
        """```json
{
  "requirements": [
    {
      "id": "CONTR-01",
      "candidate_text": "The system shall retain recent search context so users can resume a partially completed local-business search later.",
      "source_gold_requirement_id": "REQ-01",
      "source_gold_text": "ignored",
      "intended_label": "partially_fulfilled",
      "mutation_family": "persistence_extension",
      "grounding_scope": "INDIRECT_FLOW_GROUNDED",
      "requirement_type": "FR",
      "ui_evaluability": "PARTIALLY_UI_VERIFIABLE",
      "non_evaluable_reason": "BUSINESS_RULE_NOT_VISIBLE",
      "visible_subtype": "STATE_CHANGE_ACROSS_SCREENS",
      "confidence": "MEDIUM",
      "generation_rationale": "Adds a realistic persistence expectation without changing the core search capability."
    }
  ]
}
```""",
        encoding="utf-8",
    )

    contrastive_file = parse_existing_response(
        flow_id=flow_id,
        raw_response_path=raw_response_path,
        model_name="manual-chatgpt",
        generation_temperature=0.25,
        gold_root=gold_root,
        flow_root=flow_root,
        context_root=context_root,
        output_root=output_root,
    )

    saved_path = output_root / flow_id / "contrastive_candidates.json"
    assert saved_path.exists()
    saved = json.loads(saved_path.read_text(encoding="utf-8"))
    assert saved["flow_overview"] == "Harvested overview"
    assert saved["generation_model"] == "manual-chatgpt"
    assert saved["generation_temperature"] == 0.25
    assert len(saved["requirements"]) == 1
    assert saved["requirements"][0]["review_status"] == "candidate"
    assert contrastive_file.requirements[0].text.startswith("The system shall retain recent search context")
    assert (bundle_dir / "manual_contrastive_parsed.json").exists()
