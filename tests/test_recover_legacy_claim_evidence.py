from scripts.recover_legacy_claim_evidence import load_json_stream


def test_load_json_stream_reads_concatenated_objects() -> None:
    documents = load_json_stream(
        '{"flow_id": "flow-1", "items": []}\n'
        '{"flow_id": "flow-2", "items": [{"requirement_id": "REQ-01"}]}'
    )

    assert [document["flow_id"] for document in documents] == ["flow-1", "flow-2"]
