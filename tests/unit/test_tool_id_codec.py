"""Тесты для ToolIdCodec (секция 4.4 архитектуры).

Обеспечивает нормализацию tool_name ↔ server_id
с учётом дефисов/подчёркиваний и префиксов mcp__.
"""

import pytest

from cognitia.policy.tool_id_codec import DefaultToolIdCodec


@pytest.fixture
def codec() -> DefaultToolIdCodec:
    return DefaultToolIdCodec()


class TestMatches:
    """matches(tool_name, server_id) — проверка принадлежности tool к серверу."""

    def test_exact_match(self, codec: DefaultToolIdCodec) -> None:
        """mcp__iss__get_emitent_id принадлежит серверу 'iss'."""
        assert codec.matches("mcp__iss__get_emitent_id", "iss") is True

    def test_hyphen_server(self, codec: DefaultToolIdCodec) -> None:
        """mcp__iss-price__get_price_time_series принадлежит серверу 'iss-price'."""
        assert codec.matches("mcp__iss-price__get_price_time_series", "iss-price") is True

    def test_no_match(self, codec: DefaultToolIdCodec) -> None:
        """mcp__iss__get_emitent_id НЕ принадлежит серверу 'funds'."""
        assert codec.matches("mcp__iss__get_emitent_id", "funds") is False

    def test_not_mcp_tool(self, codec: DefaultToolIdCodec) -> None:
        """Bash — не MCP tool, не принадлежит никакому серверу."""
        assert codec.matches("Bash", "iss") is False

    def test_local_tool_not_matches_server(self, codec: DefaultToolIdCodec) -> None:
        """Local tool mcp__freedom_tools__calc не принадлежит серверу 'iss'."""
        assert codec.matches("mcp__freedom_tools__calculate_goal_plan", "iss") is False

    def test_local_tool_matches_own_server(self, codec: DefaultToolIdCodec) -> None:
        """Local tool matches freedom_tools server."""
        assert codec.matches("mcp__freedom_tools__calculate_goal_plan", "freedom_tools") is True


class TestEncode:
    """encode(server_id, tool_name) — построение полного tool_name."""

    def test_encode_simple(self, codec: DefaultToolIdCodec) -> None:
        """Простой server + tool -> mcp__server__tool."""
        result = codec.encode("iss", "get_emitent_id")
        assert result == "mcp__iss__get_emitent_id"

    def test_encode_hyphen_server(self, codec: DefaultToolIdCodec) -> None:
        """Server с дефисом."""
        result = codec.encode("iss-price", "get_price_time_series")
        assert result == "mcp__iss-price__get_price_time_series"


class TestExtractServer:
    """extract_server(tool_name) — извлечь server_id из tool_name."""

    def test_extract_simple(self, codec: DefaultToolIdCodec) -> None:
        """Извлечь 'iss' из 'mcp__iss__get_emitent_id'."""
        assert codec.extract_server("mcp__iss__get_emitent_id") == "iss"

    def test_extract_hyphen(self, codec: DefaultToolIdCodec) -> None:
        """Извлечь 'iss-price' из 'mcp__iss-price__get_price_time_series'."""
        assert codec.extract_server("mcp__iss-price__get_price_time_series") == "iss-price"

    def test_extract_not_mcp(self, codec: DefaultToolIdCodec) -> None:
        """Не MCP tool -> None."""
        assert codec.extract_server("Bash") is None

    def test_extract_malformed(self, codec: DefaultToolIdCodec) -> None:
        """Некорректный формат -> None."""
        assert codec.extract_server("mcp__only_one_part") is None


class TestEdgeCases:
    """Edge cases: пустые строки, множественные разделители, спецсимволы."""

    def test_empty_tool_name(self, codec: DefaultToolIdCodec) -> None:
        """Пустая строка → None."""
        assert codec.extract_server("") is None

    def test_only_mcp_prefix(self, codec: DefaultToolIdCodec) -> None:
        """Только 'mcp__' без сервера → None."""
        assert codec.extract_server("mcp__") is None

    def test_mcp_double_underscore_empty_server(self, codec: DefaultToolIdCodec) -> None:
        """'mcp____tool' — пустой server_id → None (idx=0, return None)."""
        assert codec.extract_server("mcp____tool") is None

    def test_tool_name_with_underscores(self, codec: DefaultToolIdCodec) -> None:
        """Tool name с подчёркиваниями: 'mcp__iss__get_emitent_id_full'."""
        result = codec.extract_server("mcp__iss__get_emitent_id_full")
        assert result == "iss"

    def test_tool_with_multiple_double_underscores(self, codec: DefaultToolIdCodec) -> None:
        """'mcp__server__tool__extra' — только первый __ разделяет server/tool."""
        result = codec.extract_server("mcp__server__tool__extra")
        assert result == "server"

    def test_matches_empty_server_id(self, codec: DefaultToolIdCodec) -> None:
        """Пустой server_id → False."""
        assert codec.matches("mcp__iss__get_bonds", "") is False

    def test_encode_roundtrip(self, codec: DefaultToolIdCodec) -> None:
        """encode + extract_server = roundtrip."""
        encoded = codec.encode("iss-price", "search_bonds")
        extracted = codec.extract_server(encoded)
        assert extracted == "iss-price"

    def test_matches_roundtrip(self, codec: DefaultToolIdCodec) -> None:
        """encode + matches = True."""
        encoded = codec.encode("funds", "get_fund_info")
        assert codec.matches(encoded, "funds") is True
        assert codec.matches(encoded, "iss") is False

    def test_no_mcp_prefix_with_double_underscore(self, codec: DefaultToolIdCodec) -> None:
        """'notmcp__server__tool' → None (нет mcp__ префикса)."""
        assert codec.extract_server("notmcp__server__tool") is None

    def test_server_with_numbers(self, codec: DefaultToolIdCodec) -> None:
        """Server ID с цифрами: 'server123'."""
        encoded = codec.encode("server123", "tool")
        assert codec.extract_server(encoded) == "server123"
        assert codec.matches(encoded, "server123") is True
