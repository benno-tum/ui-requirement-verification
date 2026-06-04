from __future__ import annotations

from ui_verifier.model_config import get_model_role_config


def infer_provider(model_name: str, configured_provider: str | None = None) -> str:
    if model_name.startswith("deepseek-"):
        return "deepseek"
    if model_name.startswith("gemini-"):
        return "gemini"
    return configured_provider or "gemini"


def run_text_json_llm(
    prompt: str,
    *,
    role: str,
    model_name: str | None = None,
    provider: str | None = None,
    temperature: float | None = None,
) -> str:
    config = get_model_role_config(role)
    resolved_model = model_name or config.model
    resolved_provider = infer_provider(resolved_model, provider or config.provider)
    resolved_temperature = config.temperature if temperature is None else temperature

    if resolved_provider == "gemini":
        from ui_verifier.requirements.gemini_client import run_gemini

        return run_gemini(prompt, [], resolved_model, temperature=resolved_temperature)
    if resolved_provider == "deepseek":
        from ui_verifier.requirements.deepseek_client import run_deepseek_json

        return run_deepseek_json(prompt, model_name=resolved_model, temperature=resolved_temperature)
    raise ValueError(f"Unsupported text LLM provider for role {role}: {resolved_provider}")
