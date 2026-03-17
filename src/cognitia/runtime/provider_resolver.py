"""Shared ProviderResolver — единый резолвер провайдеров для всех рунтаймов.

Резолвит модель через ModelRegistry, определяет провайдера, SDK type и base_url.
Используется ThinRuntime, DeepAgentsRuntime и portable path.

SDK types:
- "anthropic" → anthropic SDK (messages API)
- "openai_compat" → openai SDK (chat.completions API, покрывает OpenAI/OpenRouter/Ollama/vLLM/Groq/etc)
- "google" → google-genai SDK
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cognitia.runtime.model_registry import get_registry

SdkType = Literal["anthropic", "openai_compat", "google"]


@dataclass(frozen=True)
class ResolvedProvider:
    """Результат резолва провайдера."""

    model_id: str
    provider: str
    sdk_type: SdkType
    base_url: str | None


# Провайдеры с OpenAI-compatible API и их default base_url
_OPENAI_COMPAT_PROVIDERS: dict[str, str | None] = {
    "openai": None,  # standard OpenAI endpoint
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
    "local": "http://localhost:8000/v1",
    "together": "https://api.together.xyz/v1",
    "groq": "https://api.groq.com/openai/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "deepseek": "https://api.deepseek.com/v1",
}

# Провайдер → SDK type
_PROVIDER_SDK_MAP: dict[str, SdkType] = {
    "anthropic": "anthropic",
    "google": "google",
    **{provider: "openai_compat" for provider in _OPENAI_COMPAT_PROVIDERS},
}

def _parse_prefix(raw: str) -> tuple[str | None, str]:
    """Разобрать 'provider:model' notation.

    Returns:
        (provider, model_id) если есть prefix.
        (None, raw) если prefix нет.
    """
    if ":" not in raw:
        return None, raw

    prefix, model_part = raw.split(":", 1)
    normalized = prefix.strip().lower()

    # google_genai → google
    if normalized == "google_genai":
        normalized = "google"

    if normalized in _PROVIDER_SDK_MAP:
        return normalized, model_part.strip()

    # Не наш prefix (может быть часть model_id типа "accounts/fireworks/models/x")
    return None, raw


def _get_default_base_url(provider: str) -> str | None:
    """Default base_url для провайдера (None = стандартный endpoint SDK)."""
    return _OPENAI_COMPAT_PROVIDERS.get(provider)


def resolve_provider(
    raw_model: str | None,
    *,
    base_url: str | None = None,
) -> ResolvedProvider:
    """Резолвить модель и провайдера.

    Поддерживает:
    - Aliases: "sonnet" → claude-sonnet-4-20250514 (anthropic)
    - Explicit prefix: "openai:gpt-4o", "ollama:llama3"
    - Auto base_url: openrouter → openrouter.ai, ollama → localhost:11434
    - Custom base_url: перезаписывает auto-detected

    Args:
        raw_model: Имя модели, alias или "provider:model".
        base_url: Custom base URL (перезаписывает auto-detected).

    Returns:
        ResolvedProvider с model_id, provider, sdk_type, base_url.
    """
    registry = get_registry()

    if not raw_model or not raw_model.strip():
        default = registry.default_model
        provider = registry.get_provider(default)
        sdk_type = _PROVIDER_SDK_MAP.get(provider, "openai_compat")
        return ResolvedProvider(
            model_id=default,
            provider=provider,
            sdk_type=sdk_type,
            base_url=base_url,
        )

    explicit_provider, model_part = _parse_prefix(raw_model.strip())

    if explicit_provider is not None:
        model_id = model_part
        provider = explicit_provider
    else:
        model_id = registry.resolve(raw_model)
        provider = registry.get_provider(model_id)

    sdk_type = _PROVIDER_SDK_MAP.get(provider, "openai_compat")
    effective_base_url = base_url if base_url is not None else _get_default_base_url(provider)

    return ResolvedProvider(
        model_id=model_id,
        provider=provider,
        sdk_type=sdk_type,
        base_url=effective_base_url,
    )
