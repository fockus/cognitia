"""Cognitia Plugin System — entry-point-based discovery and loading."""

from __future__ import annotations

from cognitia.plugins.runner import PluginRunner, SubprocessPluginRunner
from cognitia.plugins.runner_types import PluginHandle, PluginManifest, PluginState

__all__ = [
    "PluginHandle",
    "PluginManifest",
    "PluginRunner",
    "PluginState",
    "SubprocessPluginRunner",
]
