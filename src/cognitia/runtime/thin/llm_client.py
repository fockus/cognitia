"""LLM client functions для ThinRuntime.

default_llm_call     — вызов Anthropic SDK (production)
try_stream_llm_call  — streaming wrapper с fallback
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from cognitia.runtime.types import RuntimeConfig


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


async def default_llm_call(
    config: RuntimeConfig,
    messages: list[dict[str, str]],
    system_prompt: str,
    **kwargs: Any,
) -> str:
    """Default LLM call через anthropic SDK.

    Модель берётся из config.model (настраивается через
    ANTHROPIC_MODEL env, CLI --model, или RuntimeConfig).
    Base URL берётся из config.base_url или ANTHROPIC_BASE_URL env
    (для OpenRouter, proxy и т.д.).
    """
    import logging
    import os

    logger = logging.getLogger(__name__)

    try:
        import anthropic
    except ImportError:
        return json.dumps(
            {
                "type": "final",
                "final_message": (
                    "anthropic SDK не установлен. Установите: pip install cognitia[thin]"
                ),
            }
        )

    # Base URL: config > env > стандартный Anthropic
    base_url = config.base_url or os.getenv("ANTHROPIC_BASE_URL", "").strip() or None

    client_kwargs: dict[str, Any] = {}
    if base_url:
        client_kwargs["base_url"] = base_url
        logger.info("LLM base_url: %s", base_url)

    client = anthropic.AsyncAnthropic(**client_kwargs)

    # Конвертируем messages (убираем system из списка)
    api_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m["role"] in ("user", "assistant")
    ]

    if not api_messages:
        api_messages = [{"role": "user", "content": "Привет"}]

    model = config.model
    logger.info("LLM запрос: model=%s, messages=%d", model, len(api_messages))

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=api_messages,  # type: ignore[arg-type]
        )
    except anthropic.AuthenticationError as e:
        error_msg = (
            f"Ошибка аутентификации LLM API: {e}. "
            "Проверьте ANTHROPIC_API_KEY и ANTHROPIC_BASE_URL в .env"
        )
        logger.error(error_msg)
        return json.dumps({"type": "final", "final_message": error_msg})
    except anthropic.APIConnectionError as e:
        error_msg = f"Не удалось подключиться к LLM API: {e}"
        logger.error(error_msg)
        return json.dumps({"type": "final", "final_message": error_msg})
    except anthropic.APIStatusError as e:
        error_msg = f"Ошибка LLM API (status={e.status_code}): {e.message}"
        logger.error(error_msg)
        return json.dumps({"type": "final", "final_message": error_msg})
    except Exception as e:
        error_msg = f"Неожиданная ошибка LLM API: {type(e).__name__}: {e}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"type": "final", "final_message": error_msg})

    # Извлекаем текст из response
    text_parts = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)

    logger.info(
        "LLM ответ: model=%s, tokens_in=%s, tokens_out=%s",
        getattr(response, "model", model),
        getattr(response.usage, "input_tokens", "?"),
        getattr(response.usage, "output_tokens", "?"),
    )
    return "".join(text_parts)
