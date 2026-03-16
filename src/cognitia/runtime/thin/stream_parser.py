"""Incremental JSON parsers для token-level streaming.

IncrementalEnvelopeParser — low-level parser, возвращает raw dict.
StreamParser — high-level parser, возвращает ActionEnvelope.

Собирает JSON объект из потока text chunks. Возвращает parsed result
как только обнаружен полный верхнеуровневый JSON объект.
"""

from __future__ import annotations

import json
from typing import Any

from cognitia.runtime.thin.schemas import ActionEnvelope


class IncrementalEnvelopeParser:
    """Incremental JSON envelope parser.

    feed(chunk) собирает буфер, отслеживает depth фигурных скобок.
    Как только depth вернулся к 0 после открывающей { — парсит JSON.
    """

    def __init__(self) -> None:
        self._buffer: list[str] = []
        self._depth: int = 0
        self._started: bool = False
        self._in_string: bool = False
        self._escape: bool = False

    def feed(self, chunk: str) -> dict[str, Any] | None:
        """Добавить chunk текста. Вернуть parsed dict если JSON полный, иначе None."""
        for ch in chunk:
            if self._in_string:
                self._buffer.append(ch)
                if self._escape:
                    self._escape = False
                elif ch == "\\":
                    self._escape = True
                elif ch == '"':
                    self._in_string = False
                continue

            if ch == '"':
                self._in_string = True
                if self._started:
                    self._buffer.append(ch)
                else:
                    # Text before JSON — skip
                    pass
                continue

            if ch == "{":
                if not self._started:
                    self._started = True
                self._depth += 1
                self._buffer.append(ch)
                continue

            if ch == "}":
                if self._started:
                    self._depth -= 1
                    self._buffer.append(ch)
                    if self._depth == 0:
                        return self._try_parse()
                continue

            if self._started:
                self._buffer.append(ch)

        return None

    def finalize(self) -> dict[str, Any] | None:
        """Попытка распарсить буфер как есть (финализация stream)."""
        if not self._started:
            return None
        return self._try_parse()

    def get_buffered_text(self) -> str:
        """Вернуть накопленный текст (для fallback)."""
        return "".join(self._buffer)

    def _try_parse(self) -> dict[str, Any] | None:
        """Попытка распарсить буфер."""
        text = "".join(self._buffer)
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass
        return None


class StreamParser:
    """High-level incremental parser — собирает JSON из stream токенов.

    Буферизует входящие token chunks и пытается извлечь
    ActionEnvelope как только JSON-объект будет полным.
    В отличие от IncrementalEnvelopeParser, возвращает типизированный
    ActionEnvelope и отслеживает ошибки валидации.
    """

    def __init__(self) -> None:
        self._buffer = ""
        self._parsed: ActionEnvelope | None = None
        self._error: str | None = None

    @property
    def has_result(self) -> bool:
        """True если парсинг завершён (успех или ошибка)."""
        return self._parsed is not None or self._error is not None

    @property
    def result(self) -> ActionEnvelope | None:
        """Распарсенный ActionEnvelope или None."""
        return self._parsed

    @property
    def error(self) -> str | None:
        """Сообщение об ошибке или None."""
        return self._error

    @property
    def buffer(self) -> str:
        """Накопленный текст буфера."""
        return self._buffer

    def feed(self, chunk: str) -> bool:
        """Feed a token chunk. Returns True if parsing is complete."""
        self._buffer += chunk
        return self._try_parse()

    def _try_parse(self) -> bool:
        """Try to parse buffer as JSON. Returns True if complete."""
        stripped = self._buffer.strip()
        if not stripped:
            return False

        # Strip markdown fences
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            inner: list[str] = []
            started = False
            for line in lines:
                if line.strip().startswith("```") and not started:
                    started = True
                    continue
                if line.strip() == "```" and started:
                    break
                if started:
                    inner.append(line)
            stripped = "\n".join(inner).strip()
            if not stripped:
                return False

        # Find JSON object boundaries
        start = stripped.find("{")
        if start == -1:
            return False

        depth = 0
        in_string = False
        escape = False
        for idx in range(start, len(stripped)):
            ch = stripped[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    json_str = stripped[start : idx + 1]
                    return self._validate_envelope(json_str)
        return False

    def _validate_envelope(self, json_str: str) -> bool:
        """Validate parsed JSON as ActionEnvelope."""
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                from pydantic import ValidationError

                try:
                    self._parsed = ActionEnvelope.model_validate(data)
                    return True
                except ValidationError as e:
                    self._error = f"Invalid envelope: {e}"
                    return True
        except json.JSONDecodeError:
            pass
        return False

    def reset(self) -> None:
        """Reset parser state."""
        self._buffer = ""
        self._parsed = None
        self._error = None
