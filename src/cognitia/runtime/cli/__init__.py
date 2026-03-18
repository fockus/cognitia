"""CLI Agent Runtime — run external CLI agents via subprocess + NDJSON parsing."""

from cognitia.runtime.cli.parser import (
    ClaudeNdjsonParser,
    GenericNdjsonParser,
    NdjsonParser,
)
from cognitia.runtime.cli.types import CliConfig

__all__ = [
    "CliConfig",
    "ClaudeNdjsonParser",
    "GenericNdjsonParser",
    "NdjsonParser",
]
