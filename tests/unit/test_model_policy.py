"""Тесты для ModelPolicy."""

from cognitia.runtime.model_policy import ModelPolicy


class TestModelPolicy:
    """Тесты выбора модели."""

    def test_default_is_sonnet(self) -> None:
        """По умолчанию выбирается Sonnet."""
        policy = ModelPolicy()
        assert policy.select("coach") == "sonnet"

    def test_no_default_escalate_roles(self) -> None:
        """Без явной конфигурации роли не эскалируются."""
        policy = ModelPolicy()
        assert policy.select("strategy_planner") == "sonnet"

    def test_escalation_on_failures(self) -> None:
        """После N неудач переключается на Opus."""
        policy = ModelPolicy(escalate_on_tool_failures=3)
        assert policy.select("coach", tool_failure_count=2) == "sonnet"
        assert policy.select("coach", tool_failure_count=3) == "opus"

    def test_custom_escalate_roles(self) -> None:
        """Пользовательские роли для эскалации."""
        policy = ModelPolicy(escalate_roles={"diagnostician", "strategy_planner"})
        assert policy.select("diagnostician") == "opus"
        assert policy.select("coach") == "sonnet"
