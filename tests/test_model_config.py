from __future__ import annotations

import json

from ui_verifier.model_config import get_model_role_config, model_name_for, provider_for, temperature_for


def test_model_config_uses_repo_default_file() -> None:
    assert provider_for("claim_decomposition") == "deepseek"
    assert model_name_for("claim_decomposition") == "deepseek-chat"
    assert temperature_for("claim_decomposition") == 0.0
    assert provider_for("claim_rephrase") == "deepseek"
    assert model_name_for("claim_rephrase") == "deepseek-chat"


def test_model_config_file_and_env_overrides(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "models.json"
    config_path.write_text(
        json.dumps(
            {
                "roles": {
                    "claim_decomposition": {
                        "provider": "deepseek",
                        "model": "deepseek-v4-flash",
                        "temperature": 0.3,
                        "rationale": "test override",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("UI_VERIFIER_MODEL_CONFIG", str(config_path))

    from_file = get_model_role_config("claim_decomposition")
    assert from_file.provider == "deepseek"
    assert from_file.model == "deepseek-v4-flash"
    assert from_file.temperature == 0.3
    assert from_file.rationale == "test override"

    monkeypatch.setenv("UI_VERIFIER_CLAIM_DECOMPOSITION_PROVIDER", "gemini")
    monkeypatch.setenv("UI_VERIFIER_CLAIM_DECOMPOSITION_MODEL", "gemini-test-env")
    monkeypatch.setenv("UI_VERIFIER_CLAIM_DECOMPOSITION_TEMPERATURE", "0.1")
    from_env = get_model_role_config("claim_decomposition")
    assert from_env.provider == "gemini"
    assert from_env.model == "gemini-test-env"
    assert from_env.temperature == 0.1
