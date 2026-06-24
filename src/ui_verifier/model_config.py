from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelRoleConfig:
    role: str
    provider: str
    model: str
    temperature: float
    rationale: str | None = None


_DEFAULTS: dict[str, ModelRoleConfig] = {
    "claim_decomposition": ModelRoleConfig("claim_decomposition", "deepseek", "deepseek-chat", 0.0),
    "pipeline_claim_fallback": ModelRoleConfig("pipeline_claim_fallback", "deepseek", "deepseek-chat", 0.0),
    "evidence_retrieval": ModelRoleConfig("evidence_retrieval", "deepseek", "deepseek-chat", 0.0),
    "verification": ModelRoleConfig("verification", "gemini", "gemini-2.5-flash", 0.2),
    "demo_image_verifier": ModelRoleConfig("demo_image_verifier", "gemini", "gemini-2.5-flash-lite", 0.0),
    "requirement_harvest": ModelRoleConfig("requirement_harvest", "gemini", "gemini-2.5-flash", 0.0),
    "api_requirement_harvest": ModelRoleConfig("api_requirement_harvest", "gemini", "gemini-2.5-flash", 0.7),
    "candidate_rewrite": ModelRoleConfig("candidate_rewrite", "gemini", "gemini-2.5-flash-lite", 0.0),
    "claim_rephrase": ModelRoleConfig("claim_rephrase", "deepseek", "deepseek-chat", 0.1),
    "screen_description": ModelRoleConfig("screen_description", "gemini", "gemini-2.5-flash", 0.2),
    "contrastive_generation": ModelRoleConfig("contrastive_generation", "external", "user-provided-model", 0.2),
}


def default_model_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "models.json"


def model_config_path() -> Path:
    raw = os.environ.get("UI_VERIFIER_MODEL_CONFIG")
    return Path(raw).expanduser() if raw else default_model_config_path()


def _env_prefix(role: str) -> str:
    return "UI_VERIFIER_" + role.upper().replace("-", "_")


def _load_file_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid model config JSON: {path}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"Model config must be a JSON object: {path}")
    roles = parsed.get("roles", {})
    if not isinstance(roles, dict):
        raise ValueError(f"Model config 'roles' must be an object: {path}")
    return roles


def _temperature(value: Any, *, role: str) -> float:
    try:
        temperature = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid temperature for model role {role}: {value!r}") from exc
    if temperature < 0:
        raise ValueError(f"Temperature for model role {role} must be non-negative")
    return temperature


def get_model_role_config(role: str) -> ModelRoleConfig:
    base = _DEFAULTS.get(role)
    if base is None:
        raise KeyError(f"Unknown model role: {role}")

    file_roles = _load_file_config(model_config_path())
    file_entry = file_roles.get(role, {})
    if file_entry is None:
        file_entry = {}
    if not isinstance(file_entry, dict):
        raise ValueError(f"Model config for role {role} must be an object")

    provider = str(file_entry.get("provider") or base.provider)
    model = str(file_entry.get("model") or base.model)
    temperature = _temperature(file_entry.get("temperature", base.temperature), role=role)
    rationale = file_entry.get("rationale", base.rationale)
    rationale = str(rationale) if rationale is not None else None

    prefix = _env_prefix(role)
    provider = os.environ.get(f"{prefix}_PROVIDER", provider)
    model = os.environ.get(f"{prefix}_MODEL", model)
    if f"{prefix}_TEMPERATURE" in os.environ:
        temperature = _temperature(os.environ[f"{prefix}_TEMPERATURE"], role=role)

    return ModelRoleConfig(role=role, provider=provider, model=model, temperature=temperature, rationale=rationale)


def provider_for(role: str) -> str:
    return get_model_role_config(role).provider


def model_name_for(role: str) -> str:
    return get_model_role_config(role).model


def temperature_for(role: str) -> float:
    return get_model_role_config(role).temperature


def all_model_role_configs() -> dict[str, dict[str, Any]]:
    roles = sorted(_DEFAULTS)
    return {role: get_model_role_config(role).__dict__ for role in roles}
