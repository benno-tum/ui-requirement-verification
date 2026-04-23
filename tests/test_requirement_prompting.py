from ui_verifier.requirements.prompting import build_candidate_rewrite_prompt, build_prompt


def test_harvest_prompt_encourages_broad_feature_level_requirements() -> None:
    prompt = build_prompt(
        {"confirmed_task": "Find a nearby store", "website": "GameStop", "domain": "shopping"},
        [1, 5, 10],
    )

    assert "comprehensive harvested requirement set" in prompt
    assert "The UI is grounding evidence for the requirement, not the main subject of the requirement." in prompt
    assert "Do NOT impose an artificial upper bound on the number of requirements." in prompt
    assert "Requirement sets should not be dominated by tiny field-level widget claims." in prompt
    assert "DIRECT_FLOW_GROUNDED" in prompt
    assert "INDIRECT_FLOW_GROUNDED" in prompt
    assert "NEARBY_VARIANT" in prompt


def test_candidate_rewrite_prompt_preserves_feature_level_wording() -> None:
    prompt = build_candidate_rewrite_prompt({"requirements": []})

    assert "Keep the requirement focused on a feature or capability" in prompt
    assert "Preserve feature-level wording when it remains visibly reviewable" in prompt
    assert "The system shall display a button, label, or dropdown when the real requirement is a broader feature." in prompt
