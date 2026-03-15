"""Тесты для ModelPolicy.select_for_turn() — keyword triggers (секция 3.2 архитектуры).

Триггеры Opus:
- Слова: 'план', 'стратеги', 'пошагово', 'дорожн'
- 2+ skills одновременно
- Fallback на Sonnet
"""

from cognitia.runtime.model_policy import ModelPolicy


class TestSelectForTurn:
    """select_for_turn() — расширенный выбор модели."""

    def test_default_sonnet(self) -> None:
        """Обычный запрос → sonnet."""
        policy = ModelPolicy()
        result = policy.select_for_turn(
            role_id="coach",
            user_text="привет",
            active_skill_count=0,
        )
        assert result == "sonnet"

    def test_keyword_plan_triggers_opus(self) -> None:
        """Слово 'план' → opus."""
        policy = ModelPolicy()
        result = policy.select_for_turn(
            role_id="coach",
            user_text="составь план на год",
            active_skill_count=0,
        )
        assert result == "opus"

    def test_keyword_strategy_triggers_opus(self) -> None:
        """'стратеги' → opus."""
        policy = ModelPolicy()
        result = policy.select_for_turn(
            role_id="coach",
            user_text="нужна стратегия",
            active_skill_count=0,
        )
        assert result == "opus"

    def test_keyword_step_by_step_triggers_opus(self) -> None:
        """'пошагово' → opus."""
        policy = ModelPolicy()
        result = policy.select_for_turn(
            role_id="coach",
            user_text="объясни пошагово",
            active_skill_count=0,
        )
        assert result == "opus"

    def test_multi_skills_triggers_opus(self) -> None:
        """2+ skills → opus."""
        policy = ModelPolicy()
        result = policy.select_for_turn(
            role_id="coach",
            user_text="покажи облигации",
            active_skill_count=2,
        )
        assert result == "opus"

    def test_one_skill_stays_sonnet(self) -> None:
        """1 skill → sonnet (если нет keywords)."""
        policy = ModelPolicy()
        result = policy.select_for_turn(
            role_id="coach",
            user_text="покажи вклады",
            active_skill_count=1,
        )
        assert result == "sonnet"

    def test_role_escalates_when_configured(self) -> None:
        """Роль эскалируется, только если явно указана в escalate_roles."""
        policy = ModelPolicy(escalate_roles={"strategy_planner"})
        result = policy.select_for_turn(
            role_id="strategy_planner",
            user_text="привет",
            active_skill_count=0,
        )
        assert result == "opus"

    def test_old_select_still_works(self) -> None:
        """Обратная совместимость: старый select() работает."""
        policy = ModelPolicy()
        assert policy.select("coach") == "sonnet"
        assert policy.select("strategy_planner") == "sonnet"
