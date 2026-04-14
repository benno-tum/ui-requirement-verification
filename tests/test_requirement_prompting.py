from ui_verifier.requirements.prompting import build_candidate_rewrite_prompt, build_prompt


def test_harvest_prompt_encourages_broad_feature_level_requirements() -> None:
    prompt = build_prompt(
        {"confirmed_task": "Find a nearby store", "website": "GameStop", "domain": "shopping"},
        [1, 5, 10],
    )

    assert "meaningful software features or capabilities" in prompt
    assert "The UI is evidence for the requirement, not the main subject of the requirement." in prompt
    assert "It is acceptable that not all generated requirements fully apply to the current flow." in prompt
    assert "Be as broad as possible within the plausible feature space suggested by the shown system, task, and UI flow." in prompt
    assert "Requirements from similar systems are acceptable" in prompt


def test_candidate_rewrite_prompt_preserves_feature_level_wording() -> None:
    prompt = build_candidate_rewrite_prompt({"requirements": []})

    assert "Keep the requirement focused on a feature or capability" in prompt
    assert "Preserve feature-level wording when it remains visibly reviewable" in prompt
    assert "The system shall display a button, label, or dropdown when the real requirement is a broader feature." in prompt
