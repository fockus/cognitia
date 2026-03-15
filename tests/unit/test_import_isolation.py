"""Smoke: import cognitia modules without optional extras.

Verifies that `import cognitia` and core submodules work
when optional dependencies (claude_agent_sdk, anthropic, langchain) are absent.
"""

from __future__ import annotations

import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any


@contextmanager
def _block_packages(*names: str) -> Generator[None, None, None]:
    """Temporarily make packages unimportable."""
    saved: dict[str, Any] = {}
    saved_cognitia = {
        key: value
        for key, value in sys.modules.items()
        if key == "cognitia" or key.startswith("cognitia.")
    }
    for name in names:
        # Block the package itself and all subpackages already loaded
        keys_to_block = [k for k in sys.modules if k == name or k.startswith(f"{name}.")]
        for k in keys_to_block:
            saved[k] = sys.modules.pop(k)
        # Sentinel that prevents import
        sys.modules[name] = None  # type: ignore[assignment]
    try:
        yield
    finally:
        # Restore
        for name in names:
            sys.modules.pop(name, None)
        for key in list(sys.modules):
            if key == "cognitia" or key.startswith("cognitia."):
                sys.modules.pop(key)
        sys.modules.update(saved)
        sys.modules.update(saved_cognitia)


# -- Core library (no optional deps) --


class TestCoreImportsWithoutOptionalDeps:
    """Import core cognitia without any optional dependencies."""

    def test_import_cognitia_top_level(self) -> None:
        """Top-level `import cognitia` must work without optional deps."""
        with _block_packages(
            "claude_agent_sdk", "anthropic", "langchain_core", "langchain_anthropic"
        ):
            # Force reimport
            for key in list(sys.modules):
                if key.startswith("cognitia"):
                    del sys.modules[key]
            import cognitia

            assert hasattr(cognitia, "__version__")

    def test_import_runtime_types(self) -> None:
        with _block_packages(
            "claude_agent_sdk", "anthropic", "langchain_core", "langchain_anthropic"
        ):
            for key in list(sys.modules):
                if key.startswith("cognitia.runtime"):
                    del sys.modules[key]
            from cognitia.runtime.types import Message

            assert Message is not None

    def test_import_runtime_factory(self) -> None:
        with _block_packages(
            "claude_agent_sdk", "anthropic", "langchain_core", "langchain_anthropic"
        ):
            for key in list(sys.modules):
                if key.startswith("cognitia.runtime"):
                    del sys.modules[key]
            from cognitia.runtime.factory import RuntimeFactory

            assert RuntimeFactory is not None

    def test_import_memory(self) -> None:
        with _block_packages(
            "claude_agent_sdk", "anthropic", "langchain_core", "langchain_anthropic"
        ):
            for key in list(sys.modules):
                if key.startswith("cognitia.memory"):
                    del sys.modules[key]
            from cognitia.memory import InMemoryMemoryProvider

            assert InMemoryMemoryProvider is not None

    def test_import_context(self) -> None:
        with _block_packages("claude_agent_sdk"):
            for key in list(sys.modules):
                if key.startswith("cognitia.context"):
                    del sys.modules[key]
            from cognitia.context import DefaultContextBuilder

            assert DefaultContextBuilder is not None

    def test_import_policy(self) -> None:
        with _block_packages("claude_agent_sdk"):
            for key in list(sys.modules):
                if key.startswith("cognitia.policy"):
                    del sys.modules[key]
            from cognitia.policy import DefaultToolPolicy

            assert DefaultToolPolicy is not None

    def test_import_routing(self) -> None:
        with _block_packages("claude_agent_sdk"):
            for key in list(sys.modules):
                if key.startswith("cognitia.routing"):
                    del sys.modules[key]
            from cognitia.routing import KeywordRoleRouter

            assert KeywordRoleRouter is not None

    def test_import_hooks_without_sdk(self) -> None:
        """hooks module works without claude_agent_sdk."""
        with _block_packages("claude_agent_sdk"):
            for key in list(sys.modules):
                if key.startswith("cognitia.hooks"):
                    del sys.modules[key]
            from cognitia.hooks import HookRegistry

            assert HookRegistry is not None

    def test_import_agent_module(self) -> None:
        """Agent facade imports without optional deps."""
        with _block_packages(
            "claude_agent_sdk", "anthropic", "langchain_core", "langchain_anthropic"
        ):
            for key in list(sys.modules):
                if key.startswith("cognitia.agent"):
                    del sys.modules[key]
            from cognitia.agent import Agent

            assert Agent is not None

    def test_block_packages_restores_cognitia_module_identity(self) -> None:
        """Isolation helper восстанавливает исходные cognitia module objects."""
        from cognitia.memory_bank.types import MemoryBankViolation

        original = MemoryBankViolation

        with _block_packages("claude_agent_sdk"):
            for key in list(sys.modules):
                if key.startswith("cognitia.memory_bank"):
                    del sys.modules[key]
            from cognitia.memory_bank.types import MemoryBankViolation as reimported

            assert reimported is not original

        from cognitia.memory_bank.types import MemoryBankViolation as restored

        assert restored is original
