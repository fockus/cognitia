"""Тесты для portable memory — lightweight AGENTS.md support."""

from __future__ import annotations

import pytest

from cognitia.runtime.portable_memory import (
    inject_memory_into_prompt,
    load_agents_md,
)


class TestLoadAgentsMd:
    """load_agents_md() читает и мержит файлы."""

    def test_reads_single_file(self, tmp_path) -> None:
        p = tmp_path / "AGENTS.md"
        p.write_text("# My project\nPrefer snake_case")
        content = load_agents_md([str(p)])
        assert "snake_case" in content

    def test_skips_missing_files(self) -> None:
        content = load_agents_md(["/nonexistent/AGENTS.md"])
        assert content == ""

    def test_merges_multiple_files(self, tmp_path) -> None:
        (tmp_path / "global.md").write_text("Global rules")
        (tmp_path / "project.md").write_text("Project rules")
        content = load_agents_md(
            [str(tmp_path / "global.md"), str(tmp_path / "project.md")]
        )
        assert "Global rules" in content
        assert "Project rules" in content

    def test_empty_list_returns_empty(self) -> None:
        assert load_agents_md([]) == ""

    def test_truncates_large_files(self, tmp_path) -> None:
        """Файлы > 10KB обрезаются."""
        p = tmp_path / "large.md"
        p.write_text("x" * 20_000)
        content = load_agents_md([str(p)])
        assert len(content) <= 10_240 + 100  # 10KB + separator overhead


class TestInjectMemoryIntoPrompt:
    """inject_memory_into_prompt() добавляет XML блок."""

    def test_injects_memory_block(self) -> None:
        result = inject_memory_into_prompt("You are helpful", "Use snake_case")
        assert "<agent_memory>" in result
        assert "Use snake_case" in result
        assert result.startswith("You are helpful")

    def test_empty_content_no_block(self) -> None:
        result = inject_memory_into_prompt("You are helpful", "")
        assert "<agent_memory>" not in result
        assert result == "You are helpful"

    def test_preserves_original_prompt(self) -> None:
        result = inject_memory_into_prompt("Original prompt", "Memory")
        assert "Original prompt" in result
        assert "Memory" in result
