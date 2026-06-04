from __future__ import annotations

from ui_verifier.requirements.deepseek_client import _usage_from_openai_compatible
from ui_verifier.requirements.llm_client import infer_provider


def test_infer_provider_from_model_name() -> None:
    assert infer_provider("deepseek-v4-flash") == "deepseek"
    assert infer_provider("gemini-2.5-flash-lite") == "gemini"
    assert infer_provider("custom-model", "deepseek") == "deepseek"


def test_deepseek_usage_mapping_does_not_double_count_reasoning() -> None:
    usage = _usage_from_openai_compatible(
        {
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "prompt_cache_hit_tokens": 3,
                "completion_tokens_details": {"reasoning_tokens": 2},
            }
        }
    )
    assert usage == {
        "input_tokens": 10,
        "output_tokens": 5,
        "total_tokens": 15,
        "cached_content_tokens": 3,
        "thoughts_tokens": 0,
    }
