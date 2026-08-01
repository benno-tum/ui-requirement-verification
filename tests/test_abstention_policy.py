from ui_verifier.evaluation.abstention_policy import forced_evidence_label, reaggregate_without_abstention


def _result(*, label: str = "ABSTAIN", status: str = "MISSING", evidence: bool = False) -> dict:
    evidence_items = [{"step_index": 1}] if evidence else []
    return {
        "final_label": label,
        "claims": [{"is_core": True, "status": status, "evidence": evidence_items}],
        "evidence": evidence_items,
        "metadata": {},
    }


def test_forced_policy_uses_supported_evidence() -> None:
    label, _ = forced_evidence_label(_result(status="SUPPORTED", evidence=True))
    assert label == "FULFILLED"


def test_forced_policy_maps_missing_evidence_to_negative() -> None:
    label, _ = forced_evidence_label(_result(status="MISSING", evidence=False))
    assert label == "NOT_FULFILLED"


def test_reaggregation_only_changes_abstentions() -> None:
    run = {"metadata": {}, "results": [_result(), _result(label="PARTIALLY_FULFILLED")]}
    output = reaggregate_without_abstention(run)

    assert output["results"][0]["final_label"] == "NOT_FULFILLED"
    assert output["results"][1]["final_label"] == "PARTIALLY_FULFILLED"
    assert output["metadata"]["abstention_policy_ablation"]["changed_abstentions"] == 1
