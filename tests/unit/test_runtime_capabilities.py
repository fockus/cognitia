"""Unit: runtime capability descriptors и требования."""

from __future__ import annotations

import pytest
from cognitia.runtime.capabilities import (
    CapabilityRequirements,
    get_runtime_capabilities,
)


class TestCapabilityRequirements:
    """CapabilityRequirements — валидация и сравнение."""

    def test_invalid_tier_raises(self) -> None:
        with pytest.raises(ValueError, match="tier"):
            CapabilityRequirements(tier="unknown")  # type: ignore[arg-type]

    def test_invalid_flag_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown capability flags"):
            CapabilityRequirements(flags=("unknown_flag",))


class TestRuntimeCapabilities:
    """get_runtime_capabilities() — descriptor per runtime."""

    def test_claude_sdk_is_full_tier(self) -> None:
        caps = get_runtime_capabilities("claude_sdk")
        assert caps.runtime_name == "claude_sdk"
        assert caps.tier == "full"
        assert caps.supports_mcp is True
        assert caps.supports_interrupt is True
        assert caps.supports_resume is True

    def test_deepagents_is_full_tier(self) -> None:
        caps = get_runtime_capabilities("deepagents")
        assert caps.runtime_name == "deepagents"
        assert caps.tier == "full"
        assert caps.supports_resume is True
        assert caps.supports_interrupt is False
        assert caps.supports_user_input is False
        assert caps.supports_hitl is False
        assert caps.supports_builtin_todo is True
        assert caps.supports_native_subagents is True
        assert caps.supports_provider_override is True

    def test_thin_is_light_tier(self) -> None:
        caps = get_runtime_capabilities("thin")
        assert caps.runtime_name == "thin"
        assert caps.tier == "light"
        assert caps.supports_provider_override is True

    def test_supports_returns_false_for_missing_requirements(self) -> None:
        caps = get_runtime_capabilities("thin")
        req = CapabilityRequirements(
            tier="full",
            flags=("hitl", "native_permissions"),
        )
        assert caps.supports(req) is False
        assert set(caps.missing(req)) == {
            "tier:full",
            "hitl",
            "native_permissions",
        }

    def test_supports_returns_true_for_supported_requirements(self) -> None:
        caps = get_runtime_capabilities("claude_sdk")
        req = CapabilityRequirements(flags=("mcp", "interrupt", "resume"))
        assert caps.supports(req) is True
        assert caps.missing(req) == ()
