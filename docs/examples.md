# Examples

## 1. Financial AI Coach

An agent that helps users with personal finance: deposit matching, portfolio analysis, PF5 diagnostics.

```python
from pathlib import Path

from cognitia.bootstrap.stack import CognitiaStack
from cognitia.memory_bank.fs_provider import FilesystemMemoryBankProvider
from cognitia.memory_bank.types import MemoryBankConfig
from cognitia.runtime.types import RuntimeConfig
from cognitia.todo.inmemory_provider import InMemoryTodoProvider

# Memory bank for long-term user preference storage
memory = FilesystemMemoryBankProvider(
    MemoryBankConfig(enabled=True, root_path=Path("/data/memory")),
    user_id="client-123", topic_id="finance",
)

# Todo for tracking diagnostic tasks
todo = InMemoryTodoProvider(user_id="client-123", topic_id="finance")

stack = CognitiaStack.create(
    prompts_dir=Path("prompts"),       # identity: "You are a financial coach"
    skills_dir=Path("skills"),         # MCP: finuslugi, iss, funds
    project_root=Path("."),
    runtime_config=RuntimeConfig(runtime_name="thin", model="sonnet"),
    memory_bank_provider=memory,       # agent remembers preferences
    todo_provider=todo,                # agent tracks diagnostic checklist
    thinking_enabled=True,             # CoT for analysis
)
# Flow: thinking → todo checklist → memory_write decisions
```

---

## 2. Code Reviewer

An agent that reads code, finds issues, and suggests fixes. Runs in a sandbox with read-only access.

```python
from pathlib import Path

from cognitia.bootstrap.stack import CognitiaStack
from cognitia.runtime.types import RuntimeConfig
from cognitia.tools.sandbox_local import LocalSandboxProvider
from cognitia.tools.types import SandboxConfig

sandbox = LocalSandboxProvider(SandboxConfig(
    root_path="/projects",
    user_id="dev-team",
    topic_id="pr-456",
    denied_commands=frozenset({"rm", "git push", "sudo"}),
))

stack = CognitiaStack.create(
    prompts_dir=Path("prompts"),       # identity: "You are a senior developer"
    skills_dir=Path("skills"),
    project_root=Path("."),
    runtime_config=RuntimeConfig(runtime_name="thin", model="opus"),
    sandbox_provider=sandbox,
    thinking_enabled=True,
    allowed_system_tools={"bash", "read", "glob", "grep"},  # read-only
)
# Flow: grep code → thinking → identify issues → report
```

---

## 3. Research Assistant

An agent that searches the web, structures knowledge, and keeps notes in Memory Bank.

```python
from pathlib import Path

from cognitia.bootstrap.stack import CognitiaStack
from cognitia.memory_bank.fs_provider import FilesystemMemoryBankProvider
from cognitia.memory_bank.types import MemoryBankConfig
from cognitia.runtime.types import RuntimeConfig
from cognitia.tools.web_httpx import HttpxWebProvider

web = HttpxWebProvider(timeout=30)
memory = FilesystemMemoryBankProvider(
    MemoryBankConfig(
        enabled=True,
        root_path=Path("/data/research"),
        default_folders=["sources", "notes", "summaries"],
    ),
    user_id="researcher-1", topic_id="ai-trends-2026",
)

stack = CognitiaStack.create(
    prompts_dir=Path("prompts"),       # identity: "You are a research assistant"
    skills_dir=Path("skills"),
    project_root=Path("."),
    web_provider=web,                  # search + fetch
    memory_bank_provider=memory,       # notes and sources
    thinking_enabled=True,
)
# Flow: web_search → web_fetch → thinking → memory_write("sources/...") → report
```

---

## 4. DevOps Bot with Docker Sandbox

An agent that runs scripts in an isolated Docker container for production deployments.

```python
from pathlib import Path

from cognitia.bootstrap.stack import CognitiaStack
from cognitia.runtime.types import RuntimeConfig
from cognitia.tools.sandbox_docker import DockerSandboxProvider
from cognitia.tools.types import SandboxConfig

sandbox = DockerSandboxProvider(
    SandboxConfig(
        root_path="/workspace",
        user_id="ops-team",
        topic_id="deploy-v2",
        timeout_seconds=120,
    ),
    _container=docker_client.containers.run("python:3.12-slim", detach=True),
)

stack = CognitiaStack.create(
    prompts_dir=Path("prompts"),
    skills_dir=Path("skills"),
    project_root=Path("."),
    sandbox_provider=sandbox,
    allowed_system_tools={"bash", "read", "write", "ls"},
    thinking_enabled=True,
)
# Flow: bash("pip install ...") → write("deploy.py") → bash("python deploy.py")
```

---

## 5. Market Analysis Team

A lead agent coordinating a researcher, analyst, and writer using `TeamManager`.

```python
from cognitia.orchestration.deepagents_team import DeepAgentsTeamOrchestrator
from cognitia.orchestration.subagent_types import SubagentSpec
from cognitia.orchestration.team_manager import TeamManager
from cognitia.orchestration.team_types import TeamConfig
from cognitia.orchestration.thin_subagent import ThinSubagentOrchestrator

sub_orch = ThinSubagentOrchestrator(max_concurrent=3)
team_orch = DeepAgentsTeamOrchestrator(sub_orch)
team_mgr = TeamManager(team_orch)

config = TeamConfig(
    lead_prompt="You are a team lead. Coordinate the team for market analysis.",
    worker_specs=[
        SubagentSpec(name="researcher", system_prompt="Search for market data"),
        SubagentSpec(name="analyst", system_prompt="Analyze data and draw conclusions"),
        SubagentSpec(name="writer", system_prompt="Write the final report"),
    ],
)

team_id = await team_mgr.start_team(config, "Deposit market analysis Q1 2026")
# Lead decomposes task → workers run in parallel → lead assembles report
```

---

## 6. Minimal Agent (Thinking + Todo only)

No sandbox, no MCP, no memory bank. Just a smart chat with checklists.

```python
from pathlib import Path

from cognitia.bootstrap.stack import CognitiaStack
from cognitia.todo.inmemory_provider import InMemoryTodoProvider

stack = CognitiaStack.create(
    prompts_dir=Path("prompts"),
    skills_dir=Path("skills"),
    project_root=Path("."),
    todo_provider=InMemoryTodoProvider(user_id="u", topic_id="t"),
    thinking_enabled=True,
)
# Flow: thinking → todo_write → response
# Tool token overhead: ~300 (minimal)
```

---

## 7. Team of Agents (Researcher, Developer, Reviewer)

A three-agent team with specialized roles. The lead distributes work, workers execute in parallel, and results are collected via message passing.

```python
from datetime import datetime

from cognitia.orchestration.deepagents_team import DeepAgentsTeamOrchestrator
from cognitia.orchestration.subagent_types import SubagentSpec
from cognitia.orchestration.team_manager import TeamManager
from cognitia.orchestration.team_types import TeamConfig, TeamMessage
from cognitia.orchestration.thin_subagent import ThinSubagentOrchestrator

# Build orchestrator stack
sub_orch = ThinSubagentOrchestrator(max_concurrent=3)
team_orch = DeepAgentsTeamOrchestrator(sub_orch)
manager = TeamManager(team_orch)

# Define a 3-agent team with specialized roles
config = TeamConfig(
    lead_prompt=(
        "You are an engineering lead. Break tasks into research, implementation, "
        "and review phases. Assign work to the appropriate team member."
    ),
    worker_specs=[
        SubagentSpec(
            name="researcher",
            system_prompt="You research APIs, libraries, and best practices. Return structured findings.",
        ),
        SubagentSpec(
            name="developer",
            system_prompt="You write production-quality Python code following TDD and Clean Architecture.",
        ),
        SubagentSpec(
            name="reviewer",
            system_prompt="You review code for bugs, security issues, and adherence to SOLID principles.",
        ),
    ],
    max_workers=3,
    communication="message_passing",
)

# Start the team
team_id = await manager.start_team(config, "Build a rate limiter middleware")

# Check status
status = await manager.get_status(team_id)
print(f"Team state: {status.state}, messages exchanged: {status.messages_exchanged}")

# Send a message to a specific agent
await manager.send_to_agent(team_id, TeamMessage(
    from_agent="lead",
    to_agent="researcher",
    content="Find best practices for token bucket rate limiting in Python",
    timestamp=datetime.now(),
))

# Pause/resume agents as needed
await manager.pause_agent(team_id, "developer")
await manager.resume_agent(team_id, "developer")

# Stop when done
await manager.stop_team(team_id)
```

---

## 8. Code Verification Pipeline

Use `TddCodeVerifier` with `DoDStateMachine` to automatically verify code quality in a loop. The state machine runs checks (contracts, tests, linters, coverage) repeatedly until all pass or the max loop count is exceeded.

```python
from cognitia.orchestration.code_verifier import CommandResult, CommandRunner
from cognitia.orchestration.coding_standards import CodingStandardsConfig
from cognitia.orchestration.dod_state_machine import DoDStateMachine, DoDStatus
from cognitia.orchestration.tdd_code_verifier import TddCodeVerifier


# Implement CommandRunner for your environment (sandbox, subprocess, Docker, etc.)
class ShellCommandRunner:
    """Run commands via subprocess (for local dev)."""

    async def run(self, command: str) -> CommandResult:
        import asyncio
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return CommandResult(
            exit_code=proc.returncode or 0,
            stdout=stdout.decode(),
            stderr=stderr.decode(),
        )


# Configure coding standards (use a preset or customize)
standards = CodingStandardsConfig.strict()  # TDD + SOLID + 95% coverage
# Or customize:
# standards = CodingStandardsConfig(tdd_enabled=True, solid_enabled=True, min_coverage_pct=85)

# Create verifier and state machine
runner = ShellCommandRunner()
verifier = TddCodeVerifier(config=standards, runner=runner)
dod = DoDStateMachine(max_loops=3)

# Run verification — loops until all criteria pass or max_loops exceeded
result = await dod.verify_dod(
    criteria=("contracts", "tests", "linters", "coverage"),
    verifier=verifier,
)

if result.status == DoDStatus.PASSED:
    print(f"All checks passed in {result.loop_count} loop(s)")
elif result.status == DoDStatus.MAX_LOOPS_EXCEEDED:
    print(f"Failed after {result.loop_count} loops")
    print(result.verification_log)

# You can also run individual checks:
contracts_result = await verifier.verify_contracts()
print(f"Contracts: {contracts_result.status}")  # "pass", "fail", or "skip"

linters_result = await verifier.verify_linters()
print(f"Linters: {linters_result.status}, details: {linters_result.summary}")
```

---

## 9. Agent with Memory Bank

An agent that persists project knowledge across sessions using Memory Bank. The agent stores plans, progress, and lessons learned — all available in the next session.

```python
from pathlib import Path

from cognitia.bootstrap.stack import CognitiaStack
from cognitia.memory_bank.db_provider import DatabaseMemoryBankProvider
from cognitia.memory_bank.fs_provider import FilesystemMemoryBankProvider
from cognitia.memory_bank.schema import get_memory_bank_ddl
from cognitia.memory_bank.types import MemoryBankConfig
from cognitia.runtime.types import RuntimeConfig

# --- Option A: Filesystem backend (dev/CLI) ---

config = MemoryBankConfig(
    enabled=True,
    backend="filesystem",
    root_path=Path("./data/memory-banks"),
    max_file_size_bytes=100 * 1024,   # 100 KB per file
    max_depth=2,                       # e.g., "plans/feature.md"
    auto_load_on_turn=True,           # auto-inject MEMORY.md into context
    auto_load_max_lines=200,
    default_folders=["plans", "notes", "reports"],
)
mb_provider = FilesystemMemoryBankProvider(config, user_id="alice", topic_id="my-project")

# --- Option B: Database backend (production) ---

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
session_factory = async_sessionmaker(engine, expire_on_commit=False)

# Create table (run once in migration)
# for stmt in get_memory_bank_ddl(dialect="postgres"):
#     await session.execute(text(stmt))

mb_provider = DatabaseMemoryBankProvider(
    session_factory=session_factory, user_id="alice", topic_id="my-project",
)

# --- Wire into agent ---

stack = CognitiaStack.create(
    prompts_dir=Path("prompts"),
    skills_dir=Path("skills"),
    project_root=Path("."),
    runtime_config=RuntimeConfig(runtime_name="thin", model="sonnet"),
    memory_bank_provider=mb_provider,
    # Custom prompt (or omit for default):
    memory_bank_prompt=(
        "You have a Memory Bank for persisting knowledge across sessions.\n"
        "Use memory_write to save important decisions, plans, and progress.\n"
        "Use memory_read to recall previous context at the start of each session."
    ),
    thinking_enabled=True,
)
# The agent now has 5 tools: memory_read, memory_write, memory_append, memory_list, memory_delete
# MEMORY.md content is auto-loaded into context each turn

# --- Direct provider usage (outside agent) ---

# Session 1: save knowledge
await mb_provider.write_file("MEMORY.md", "# Project Memory\n- [plan](plans/mvp.md)")
await mb_provider.write_file("plans/mvp.md", "Phase 1: Auth module\nPhase 2: API layer")

# Session 2: recall knowledge
index = await mb_provider.read_file("MEMORY.md")
plan = await mb_provider.read_file("plans/mvp.md")
files = await mb_provider.list_files()  # ["MEMORY.md", "plans/mvp.md"]

# Append progress (append-only log)
await mb_provider.append_to_file("progress.md", "\n## 2026-03-15\n- Completed auth module")
```

---

## 10. Middleware Stack

Use `build_middleware_stack()` to compose `CostTracker`, `ToolOutputCompressor`, and `SecurityGuard` into a processing pipeline for the agent facade.

```python
from cognitia.agent.middleware import (
    BudgetExceededError,
    CostTracker,
    SecurityGuard,
    ToolOutputCompressor,
    build_middleware_stack,
)

# Quick setup with build_middleware_stack()
middleware = build_middleware_stack(
    cost_tracker=True,
    budget_usd=5.00,                           # stop if cost exceeds $5
    tool_compressor=True,
    max_result_chars=10000,                     # truncate tool output >10k chars
    security_guard=True,
    blocked_patterns=["rm -rf", "DROP TABLE"],  # block dangerous patterns
)
# Returns: (SecurityGuard, ToolOutputCompressor, CostTracker)

# Or compose manually for fine-grained control
security = SecurityGuard(block_patterns=["rm -rf /", "sudo", "curl | bash"])
compressor = ToolOutputCompressor(max_result_chars=8000)
cost = CostTracker(budget_usd=2.50)

middleware = (security, compressor, cost)

# Each middleware provides hooks that are auto-registered with the runtime:
# - SecurityGuard → PreToolUse hook: blocks tool calls with dangerous patterns
# - ToolOutputCompressor → PostToolUse hook: compresses large tool outputs
# - CostTracker → after_result: accumulates cost, raises BudgetExceededError

# SecurityGuard registers a PreToolUse hook
hooks = security.get_hooks()
print(hooks.list_events())  # ["PreToolUse"]

# ToolOutputCompressor does content-aware compression
print(compressor.compress('["a","b","c","d","e"]'))
# For large JSON arrays, keeps first 3 items + "[...N more items truncated]"

# CostTracker raises on budget overflow
try:
    # ... after multiple agent turns ...
    print(f"Total cost so far: ${cost.total_cost_usd:.4f}")
except BudgetExceededError as e:
    print(f"Budget exceeded: {e}")
    cost.reset()
```

---

## 11. Custom Hooks

Register pre/post tool use hooks to intercept, modify, or block tool calls and their results. Hooks are registered via `HookRegistry` and automatically wired into the runtime.

```python
import re
from typing import Any

from cognitia.hooks.registry import HookRegistry


# --- Pre-tool-use hook: audit + gate ---

async def audit_tool_call(**kwargs: Any) -> dict[str, Any]:
    """Log every tool call for audit trail."""
    tool_name = kwargs.get("tool_name", "")
    tool_input = kwargs.get("tool_input", {})
    print(f"[AUDIT] Tool: {tool_name}, Input keys: {list(tool_input.keys())}")
    # Return continue_ to let the call proceed
    return {"continue_": True}


async def block_write_to_config(**kwargs: Any) -> dict[str, Any]:
    """Block any write operations to config files."""
    tool_name = kwargs.get("tool_name", "")
    tool_input = kwargs.get("tool_input", {})
    if tool_name in ("write", "edit"):
        path = tool_input.get("path", "")
        if path.endswith((".env", ".yml", ".yaml", ".toml")):
            return {
                "decision": "block",
                "reason": f"Writing to config file '{path}' is not allowed",
            }
    return {"continue_": True}


# --- Post-tool-use hook: transform results ---

async def redact_secrets(**kwargs: Any) -> dict[str, Any]:
    """Redact API keys and tokens from tool output."""
    tool_result = kwargs.get("tool_result", "")
    if isinstance(tool_result, str):
        redacted = re.sub(
            r"(sk-|api_key=|token=)[a-zA-Z0-9_-]{10,}",
            r"\1[REDACTED]",
            tool_result,
        )
        if redacted != tool_result:
            return {"tool_result": redacted}
    return {"continue_": True}


# --- Register hooks ---

registry = HookRegistry()

# Global hooks (all tools)
registry.on_pre_tool_use(audit_tool_call)
registry.on_post_tool_use(redact_secrets)

# Tool-specific hook (only triggers for "write" and "edit" tools)
registry.on_pre_tool_use(block_write_to_config, matcher="write")
registry.on_pre_tool_use(block_write_to_config, matcher="edit")

# Lifecycle hooks
async def on_agent_stop(**kwargs: Any) -> None:
    print("[HOOK] Agent stopped")

async def on_prompt(**kwargs: Any) -> None:
    print("[HOOK] User prompt received")

registry.on_stop(on_agent_stop)
registry.on_user_prompt(on_prompt)

# Inspect registered events
print(registry.list_events())  # ["PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"]
print(len(registry.get_hooks("PreToolUse")))  # 3 (audit + 2 block_write)

# --- Merge registries ---

# Useful when combining hooks from middleware and custom logic
other_registry = HookRegistry()
other_registry.on_pre_tool_use(audit_tool_call)

combined = registry.merge(other_registry)
# combined has all hooks from both registries
```

---

## Integration Patterns

### Add a capability to an existing application

```python
# Before: MCP skills only
stack = CognitiaStack.create(prompts_dir=..., skills_dir=..., project_root=...)

# After: + memory bank + todo
stack = CognitiaStack.create(
    prompts_dir=..., skills_dir=..., project_root=...,
    memory_bank_provider=memory,
    todo_provider=todo,
    thinking_enabled=True,
)
```

### Switch runtime without changing code

```python
# Dev
config = RuntimeConfig(runtime_name="thin")

# Staging
config = RuntimeConfig(runtime_name="deepagents")

# Production
config = RuntimeConfig(runtime_name="claude_sdk")

# Same stack.create() — only config changes
```

### Override builtin tools

```python
class MyToolResolver:
    def resolve(self, tool_name):
        if tool_name == "memory_read":
            return my_custom_memory_read  # custom implementation
        return None

stack = CognitiaStack.create(
    ...,
    local_tool_resolver=MyToolResolver(),
)
```
