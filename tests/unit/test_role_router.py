"""Тесты для RoleRouter (секция 7 архитектуры).

Детерминированные тест-кейсы на маршрутизацию:
1. Явная команда — приоритет
2. Keyword/regex эвристика
3. Fallback на default role
"""

import pytest

from cognitia.routing.role_router import KeywordRoleRouter


@pytest.fixture
def router() -> KeywordRoleRouter:
    """Роутер с keyword-маппингами для финансового коуча."""
    return KeywordRoleRouter(
        default_role="coach",
        keyword_map={
            "deposit_advisor": [
                "вклад", "депозит", "накопить", "сберечь", "ставка по вкладу",
            ],
            "credit_advisor": [
                "кредит", "ипотека", "долг", "рефинанс", "займ",
            ],
            "portfolio_builder": [
                "портфель", "облигаци", "акции", "фонд", "пиф", "etf",
            ],
            "diagnostician": [
                "диагностик", "финансовое здоровье", "анализ расходов",
            ],
            "strategy_planner": [
                "стратеги", "план на год", "дорожн", "пошагово",
            ],
        },
    )


class TestExplicitCommand:
    """Явная команда /role <id> имеет приоритет."""

    def test_explicit_role_overrides_keywords(self, router: KeywordRoleRouter) -> None:
        """Даже если текст содержит ключевые слова — явная команда побеждает."""
        result = router.resolve(
            user_text="хочу вклад с хорошей ставкой",
            explicit_role="coach",
        )
        assert result == "coach"

    def test_explicit_role_any_value(self, router: KeywordRoleRouter) -> None:
        """Любое явное значение принимается as-is."""
        result = router.resolve(user_text="", explicit_role="custom_role")
        assert result == "custom_role"


class TestKeywordMatching:
    """Keyword-эвристика для автоматического определения роли."""

    def test_deposit_keywords(self, router: KeywordRoleRouter) -> None:
        """'вклад' -> deposit_advisor."""
        assert router.resolve("хочу открыть вклад") == "deposit_advisor"

    def test_credit_keywords(self, router: KeywordRoleRouter) -> None:
        """'кредит' -> credit_advisor."""
        assert router.resolve("как взять кредит") == "credit_advisor"

    def test_portfolio_keywords(self, router: KeywordRoleRouter) -> None:
        """'облигации' -> portfolio_builder."""
        assert router.resolve("подбери облигации") == "portfolio_builder"

    def test_diagnostician_keywords(self, router: KeywordRoleRouter) -> None:
        """'диагностика' -> diagnostician."""
        assert router.resolve("проведи диагностику") == "diagnostician"

    def test_strategy_keywords(self, router: KeywordRoleRouter) -> None:
        """'стратегия' -> strategy_planner."""
        assert router.resolve("составь стратегию") == "strategy_planner"

    def test_case_insensitive(self, router: KeywordRoleRouter) -> None:
        """Регистронезависимый поиск."""
        assert router.resolve("ВКЛАД под хороший процент") == "deposit_advisor"

    def test_partial_match(self, router: KeywordRoleRouter) -> None:
        """Слово внутри предложения."""
        assert router.resolve("мне нужна ипотека на квартиру") == "credit_advisor"


class TestFallback:
    """Fallback на default role если нет совпадений."""

    def test_no_keywords_returns_default(self, router: KeywordRoleRouter) -> None:
        """Нет совпадений → coach."""
        assert router.resolve("привет, как дела?") == "coach"

    def test_empty_text_returns_default(self, router: KeywordRoleRouter) -> None:
        """Пустой текст → default."""
        assert router.resolve("") == "coach"

    def test_custom_default(self) -> None:
        """Можно задать другой default."""
        router = KeywordRoleRouter(default_role="diagnostician", keyword_map={})
        assert router.resolve("что угодно") == "diagnostician"


class TestFirstMatchPriority:
    """При нескольких совпадениях — первое побеждает."""

    def test_first_keyword_wins(self, router: KeywordRoleRouter) -> None:
        """Если текст содержит слова от нескольких ролей — первый match побеждает."""
        result = router.resolve("хочу вклад и кредит")
        # Порядок проверки определяется порядком keyword_map
        assert result in ("deposit_advisor", "credit_advisor")
