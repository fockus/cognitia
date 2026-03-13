# Cognitia Documentation

**Cognitia** is an LLM-agnostic Python framework for building production AI agents with pluggable runtimes, persistent memory, tool management, and structured observability.

## Getting Started

- [Why Cognitia?](why-cognitia.md) — design philosophy, key advantages, comparison with alternatives
- [Getting Started](getting-started.md) — installation, your first agent in 3 lines, step-by-step guide

## Core Concepts

- [Agent Facade API](agent-facade.md) — `Agent`, `AgentConfig`, `@tool` decorator, `Result`, `Conversation`, `Middleware`
- [Runtimes](runtimes.md) — Claude SDK vs ThinRuntime vs DeepAgents: comparison, switching, capability negotiation
- [Architecture](architecture.md) — Clean Architecture layers, 14 protocols, package structure, design principles

## Data & Storage

- [Memory Providers](memory.md) — InMemory, PostgreSQL, SQLite: 8 protocols, summarization, dependency injection
- [Capabilities](capabilities.md) — sandbox, web, todo, memory bank, planning, thinking — independent toggles

## Tools & Integration

- [Tools & Skills](tools-and-skills.md) — `@tool` decorator, MCP skills (YAML), tool policy (default-deny), role-skill mapping
- [Web Tools](web-tools.md) — search providers (DuckDuckGo, Brave, Tavily, SearXNG), fetch providers (httpx, Jina, Crawl4AI)

## Configuration & Operations

- [Configuration](configuration.md) — `CognitiaStack`, `RuntimeConfig`, `ToolPolicy`, environment variables
- [Orchestration](orchestration.md) — planning mode, subagents, team mode (lead + workers)

## Reference

- [API Reference](api-reference.md) — complete API: all classes, methods, protocols, types
- [Advanced Features](advanced.md) — hooks, observability, circuit breaker, context builder, session management, role routing, model registry, commands
- [Examples](examples.md) — integration examples: finance coach, code reviewer, research assistant, DevOps, multi-agent team

## Links

- [Changelog](../CHANGELOG.md)
- [Contributing](../CONTRIBUTING.md)
- [License](../LICENSE) (MIT)
- [PyPI](https://pypi.org/project/cognitia/)
- [GitHub](https://github.com/fockus/cognitia)

## Requirements

- Python 3.10+
- Core dependencies: `structlog`, `pyyaml`, `pydantic`
- Runtimes, storage, and capabilities: installed via [extras](getting-started.md#installation)
