"""Тесты для DefaultToolPolicy."""

import pytest

from cognitia.policy import (
    ALWAYS_DENIED_TOOLS,
    DefaultToolPolicy,
    PermissionAllow,
    PermissionDeny,
    ToolPolicyInput,
)


@pytest.fixture
def policy() -> DefaultToolPolicy:
    return DefaultToolPolicy()


def _make_state(
    active_skills: list[str] | None = None,
    local_tools: set[str] | None = None,
) -> ToolPolicyInput:
    return ToolPolicyInput(
        tool_name="",
        input_data={},
        active_skill_ids=active_skills or [],
        allowed_local_tools=local_tools or set(),
    )


class TestDenyList:
    """Тесты на запрещённые инструменты."""

    def test_bash_denied(self, policy: DefaultToolPolicy) -> None:
        """Bash всегда запрещён."""
        result = policy.can_use_tool("Bash", {}, _make_state())
        assert isinstance(result, PermissionDeny)
        assert "Bash" in result.message

    def test_read_denied(self, policy: DefaultToolPolicy) -> None:
        """Read всегда запрещён."""
        result = policy.can_use_tool("Read", {}, _make_state())
        assert isinstance(result, PermissionDeny)

    def test_write_denied(self, policy: DefaultToolPolicy) -> None:
        """Write всегда запрещён."""
        result = policy.can_use_tool("Write", {}, _make_state())
        assert isinstance(result, PermissionDeny)

    def test_edit_denied(self, policy: DefaultToolPolicy) -> None:
        """Edit всегда запрещён."""
        result = policy.can_use_tool("Edit", {}, _make_state())
        assert isinstance(result, PermissionDeny)

    def test_glob_denied(self, policy: DefaultToolPolicy) -> None:
        """Glob всегда запрещён."""
        result = policy.can_use_tool("Glob", {}, _make_state())
        assert isinstance(result, PermissionDeny)

    def test_all_denied_tools_covered(self, policy: DefaultToolPolicy) -> None:
        """Все инструменты из ALWAYS_DENIED_TOOLS запрещены."""
        for tool_name in ALWAYS_DENIED_TOOLS:
            result = policy.can_use_tool(tool_name, {}, _make_state())
            assert isinstance(result, PermissionDeny), f"{tool_name} должен быть запрещён"


class TestMcpTools:
    """Тесты на MCP инструменты."""

    def test_mcp_tool_allowed_when_skill_active(self, policy: DefaultToolPolicy) -> None:
        """MCP tool разрешён, если сервер в активных скилах."""
        state = _make_state(active_skills=["iss"])
        result = policy.can_use_tool("mcp__iss__search_bonds", {}, state)
        assert isinstance(result, PermissionAllow)

    def test_mcp_tool_denied_when_skill_inactive(self, policy: DefaultToolPolicy) -> None:
        """MCP tool запрещён, если сервер не в активных скилах."""
        state = _make_state(active_skills=["finuslugi"])
        result = policy.can_use_tool("mcp__iss__search_bonds", {}, state)
        assert isinstance(result, PermissionDeny)
        assert "iss" in result.message

    def test_mcp_tool_different_servers(self, policy: DefaultToolPolicy) -> None:
        """MCP tool от finuslugi разрешён если finuslugi активен."""
        state = _make_state(active_skills=["finuslugi", "iss"])
        result = policy.can_use_tool("mcp__finuslugi__get_bank_deposits", {}, state)
        assert isinstance(result, PermissionAllow)


class TestLocalTools:
    """Тесты на локальные инструменты."""

    def test_local_tool_allowed(self, policy: DefaultToolPolicy) -> None:
        """Локальный tool разрешён если в allowed_local_tools."""
        state = _make_state(local_tools={"mcp__freedom_tools__calculate_goal_plan"})
        result = policy.can_use_tool("mcp__freedom_tools__calculate_goal_plan", {}, state)
        assert isinstance(result, PermissionAllow)

    def test_unknown_tool_denied(self, policy: DefaultToolPolicy) -> None:
        """Неизвестный tool запрещён."""
        state = _make_state()
        result = policy.can_use_tool("SomeRandomTool", {}, state)
        assert isinstance(result, PermissionDeny)


class TestAgentLoggerIntegration:
    """GAP-4: AgentLogger.tool_policy_event() вызывается в DefaultToolPolicy."""

    def test_logger_called_on_deny(self) -> None:
        """AgentLogger.tool_policy_event вызывается при deny (GAP-4)."""
        from unittest.mock import MagicMock
        mock_logger = MagicMock()
        policy = DefaultToolPolicy(agent_logger=mock_logger)
        state = _make_state()

        policy.can_use_tool("Bash", {}, state)

        mock_logger.tool_policy_event.assert_called_once_with(
            tool_name="Bash",
            allowed=False,
            reason="always_denied",
            server_id="",
        )

    def test_logger_called_on_allow(self) -> None:
        """AgentLogger.tool_policy_event вызывается при allow (GAP-4)."""
        from unittest.mock import MagicMock
        mock_logger = MagicMock()
        policy = DefaultToolPolicy(agent_logger=mock_logger)
        state = _make_state(active_skills=["iss"])

        policy.can_use_tool("mcp__iss__search_bonds", {}, state)

        mock_logger.tool_policy_event.assert_called_once_with(
            tool_name="mcp__iss__search_bonds",
            allowed=True,
            reason="mcp_active_skill",
            server_id="iss",
        )

    def test_works_without_logger(self) -> None:
        """Без AgentLogger — работает как раньше (обратная совместимость)."""
        policy = DefaultToolPolicy()
        state = _make_state(active_skills=["iss"])
        result = policy.can_use_tool("mcp__iss__search_bonds", {}, state)
        assert isinstance(result, PermissionAllow)
