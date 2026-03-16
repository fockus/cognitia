"""TDD-тесты для find_json_object_boundaries — общая утилита brace-tracking.

Покрывает: простые объекты, вложенность, escaped quotes, строки с фигурными
скобками, start offset, отсутствие JSON, незакрытые объекты.
"""

from __future__ import annotations

import pytest
from cognitia.runtime.thin.json_utils import find_json_object_boundaries


class TestFindJsonObjectBoundariesBasic:
    """Базовые сценарии поиска JSON-объекта."""

    def test_simple_object_returns_boundaries(self) -> None:
        text = '{"type": "final"}'
        result = find_json_object_boundaries(text)
        assert result == (0, 17)
        assert text[result[0] : result[1]] == '{"type": "final"}'

    def test_object_with_prefix_text(self) -> None:
        text = 'Some prefix {"key": "value"} suffix'
        result = find_json_object_boundaries(text)
        assert result is not None
        assert text[result[0] : result[1]] == '{"key": "value"}'

    def test_no_json_returns_none(self) -> None:
        assert find_json_object_boundaries("plain text without braces") is None

    def test_empty_string_returns_none(self) -> None:
        assert find_json_object_boundaries("") is None

    def test_only_opening_brace_returns_none(self) -> None:
        assert find_json_object_boundaries("{incomplete") is None


class TestFindJsonObjectBoundariesNested:
    """Вложенные объекты и массивы."""

    def test_nested_objects(self) -> None:
        text = '{"tool": {"name": "calc", "args": {"x": 1}}}'
        result = find_json_object_boundaries(text)
        assert result is not None
        assert text[result[0] : result[1]] == text

    def test_deeply_nested(self) -> None:
        text = '{"a": {"b": {"c": {"d": 1}}}}'
        result = find_json_object_boundaries(text)
        assert result is not None
        assert text[result[0] : result[1]] == text


class TestFindJsonObjectBoundariesStrings:
    """Корректная обработка строковых литералов."""

    def test_escaped_quotes_in_string(self) -> None:
        text = r'{"msg": "say \"hello\""}'
        result = find_json_object_boundaries(text)
        assert result is not None
        assert text[result[0] : result[1]] == text

    def test_braces_inside_string_ignored(self) -> None:
        text = '{"msg": "curly { braces } inside"}'
        result = find_json_object_boundaries(text)
        assert result is not None
        assert text[result[0] : result[1]] == text

    def test_escaped_backslash_before_quote(self) -> None:
        # Строка заканчивается на \\", т.е. escaped backslash + closing quote
        text = '{"path": "C:\\\\Users"}'
        result = find_json_object_boundaries(text)
        assert result is not None
        assert text[result[0] : result[1]] == text


class TestFindJsonObjectBoundariesStartOffset:
    """Параметр start для поиска с позиции."""

    def test_start_offset_skips_first_object(self) -> None:
        text = '{"a": 1} {"b": 2}'
        first = find_json_object_boundaries(text, start=0)
        assert first is not None
        assert text[first[0] : first[1]] == '{"a": 1}'

        second = find_json_object_boundaries(text, start=first[1])
        assert second is not None
        assert text[second[0] : second[1]] == '{"b": 2}'

    def test_start_beyond_text_returns_none(self) -> None:
        assert find_json_object_boundaries('{"a": 1}', start=100) is None

    def test_start_at_opening_brace(self) -> None:
        text = '  {"key": "val"}'
        result = find_json_object_boundaries(text, start=2)
        assert result is not None
        assert text[result[0] : result[1]] == '{"key": "val"}'


class TestFindJsonObjectBoundariesEdgeCases:
    """Edge cases."""

    def test_empty_object(self) -> None:
        text = "{}"
        result = find_json_object_boundaries(text)
        assert result == (0, 2)

    def test_object_at_end_of_text(self) -> None:
        text = 'prefix{"ok": true}'
        result = find_json_object_boundaries(text)
        assert result is not None
        assert text[result[0] : result[1]] == '{"ok": true}'

    @pytest.mark.parametrize(
        "text,expected_slice",
        [
            ('{"a":1}', '{"a":1}'),
            ('xx{"a":1}yy', '{"a":1}'),
            ('{"a":{"b":2}}', '{"a":{"b":2}}'),
        ],
        ids=["exact", "surrounded", "nested"],
    )
    def test_parametrized_cases(self, text: str, expected_slice: str) -> None:
        result = find_json_object_boundaries(text)
        assert result is not None
        assert text[result[0] : result[1]] == expected_slice
