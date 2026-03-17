"""LLM client functions для ThinRuntime."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from cognitia.runtime.provider_resolver import resolve_provider
from cognitia.runtime.thin.errors import ThinLlmError, provider_runtime_crash
from cognitia.runtime.thin.llm_providers import get_cached_adapter
from cognitia.runtime.types import RuntimeConfig

logger = logging.getLogger(__name__)


async def try_stream_llm_call(
    llm_call: Callable[..., Any],
    lm_messages: list[dict[str, str]],
    prompt: str,
) -> tuple[list[str], str] | None:
    """Попробовать streaming LLM вызов.

    Returns:
        (chunks, full_text) если streaming поддерживается.
        Если LLM вернула str вместо AsyncIterator -- возвращает ([full_text], full_text)
        чтобы не терять уже сделанный вызов.
        None только если LLM не поддерживает stream kwarg (TypeError).
    """
    try:
        result = await llm_call(lm_messages, prompt, stream=True)
    except TypeError:
        # LLM не поддерживает stream kwarg
        return None

    if isinstance(result, str):
        # LLM принимает stream kwarg но возвращает str -- используем как есть
        return [result], result

    if not hasattr(result, "__aiter__"):
        return None

    chunks: list[str] = []
    async for chunk in result:
        chunks.append(chunk)
    return chunks, "".join(chunks)


async def _stream_with_error_normalization(
    adapter: Any,
    provider: str,
    messages: list[dict[str, str]],
    system_prompt: str,
    **kwargs: Any,
) -> AsyncIterator[str]:
    """Wrap adapter.stream() so iteration-time failures become typed errors."""
    try:
        async for chunk in adapter.stream(messages, system_prompt, **kwargs):
            yield chunk
    except ThinLlmError:
        raise
    except Exception as exc:
        logger.error("Ошибка LLM API (%s)", provider, exc_info=True)
        raise provider_runtime_crash(provider, exc) from exc


async def default_llm_call(
    config: RuntimeConfig,
    messages: list[dict[str, str]],
    system_prompt: str,
    **kwargs: Any,
) -> str | AsyncIterator[str]:
    """Multi-provider LLM call через ProviderResolver + LlmAdapter.

    Модель берётся из config.model. ProviderResolver определяет провайдера,
    SDK type и base_url. create_llm_adapter() создаёт подходящий адаптер.

    При stream=True возвращает AsyncIterator[str] (через adapter.stream()).
    Иначе — str (через adapter.call()).

    Поддерживает: Anthropic, OpenAI, Google, OpenRouter, Ollama, Groq,
    Together, Fireworks, DeepSeek, vLLM, любой OpenAI-compatible.
    """
    use_stream = kwargs.pop("stream", False)

    resolved = resolve_provider(config.model, base_url=config.base_url)
    logger.info(
        "LLM запрос: model=%s, provider=%s, sdk=%s, stream=%s",
        resolved.model_id,
        resolved.provider,
        resolved.sdk_type,
        use_stream,
    )

    try:
        adapter = get_cached_adapter(resolved)
    except ThinLlmError:
        raise
    except Exception as exc:
        logger.error("Ошибка инициализации LLM адаптера (%s)", resolved.provider, exc_info=True)
        raise provider_runtime_crash(resolved.provider, exc) from exc

    try:
        if use_stream:
            return _stream_with_error_normalization(
                adapter,
                resolved.provider,
                messages,
                system_prompt,
                **kwargs,
            )
        return await adapter.call(messages, system_prompt, **kwargs)
    except ThinLlmError:
        raise
    except Exception as exc:
        logger.error("Ошибка LLM API (%s)", resolved.provider, exc_info=True)
        raise provider_runtime_crash(resolved.provider, exc) from exc
