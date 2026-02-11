"""ToolIdCodec — нормализация имён инструментов (секция 4.4 архитектуры).

Обеспечивает единообразную работу с tool_name/server_id
независимо от дефисов, подчёркиваний и префиксов mcp__.
"""

from __future__ import annotations

# Разделитель SDK между server и tool
_SEP = "__"
_MCP_PREFIX = "mcp"


class DefaultToolIdCodec:
    """Реализация ToolIdCodec по умолчанию.

    Формат tool_name в SDK: mcp__<server_id>__<tool_name>
    Разделитель — двойное подчёркивание.
    server_id может содержать дефисы (iss-price).
    """

    def matches(self, tool_name: str, server_id: str) -> bool:
        """Проверить, принадлежит ли tool_name данному server_id."""
        extracted = self.extract_server(tool_name)
        if extracted is None:
            return False
        return extracted == server_id

    def encode(self, server_id: str, tool_name: str) -> str:
        """Построить полное имя инструмента: mcp__<server_id>__<tool_name>."""
        return f"{_MCP_PREFIX}{_SEP}{server_id}{_SEP}{tool_name}"

    def extract_server(self, tool_name: str) -> str | None:
        """Извлечь server_id из tool_name формата mcp__<server>__<tool>.

        Поддерживает server_id с дефисами (iss-price):
        разделяем по '__' (двойное подчёркивание), а не по '_'.
        """
        if not tool_name.startswith(f"{_MCP_PREFIX}{_SEP}"):
            return None

        # Убираем префикс "mcp__"
        rest = tool_name[len(f"{_MCP_PREFIX}{_SEP}") :]

        # Ищем следующий "__" — это разделитель server/tool
        idx = rest.find(_SEP)
        if idx <= 0:
            return None

        return rest[:idx]
