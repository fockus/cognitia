# Advanced Features

## Hooks

Hooks intercept agent events for logging, security, and custom logic.

```python
from cognitia.hooks import HookRegistry

registry = HookRegistry()

# Block dangerous tools
async def block_bash(tool_name: str, tool_input: dict, **kwargs):
    if tool_name == "Bash":
        return {"decision": "deny", "reason": "Bash is not allowed"}
    return None  # allow

registry.on_pre_tool_use(block_bash, matcher="Bash")

# Log all tool calls
async def log_tool(tool_name: str, **kwargs):
    print(f"Tool called: {tool_name}")
    return None

registry.on_post_tool_use(log_tool)

# Available events: PreToolUse, PostToolUse, Stop, UserPromptSubmit
registry.on_stop(my_stop_hook)
registry.on_user_prompt(my_prompt_hook)
```

### SDK Bridge

Convert hooks to Claude Agent SDK format:

```python
from cognitia.hooks import registry_to_sdk_hooks

sdk_hooks = registry_to_sdk_hooks(registry)
# Pass to ClaudeAgentOptions.hooks
```

## Observability

Structured JSON logging via structlog:

```python
from cognitia.observability import AgentLogger, configure_logging

# Configure once at startup
configure_logging(level="info", fmt="json")

logger = AgentLogger(component="my_app")

# Structured events
logger.session_created(user_id="u1", topic_id="t1", role_id="coach")
logger.turn_start(user_id="u1", topic_id="t1")
logger.tool_call(tool_name="get_deposits", latency_ms=450)
logger.tool_policy_event(tool_name="Bash", allowed=False, reason="ALWAYS_DENIED")
logger.turn_complete(user_id="u1", topic_id="t1", role_id="coach", prompt_hash="abc123")
```

Output format:
```json
{"ts": "2026-03-13T12:00:00Z", "level": "info", "event_type": "tool_call", "tool_name": "get_deposits", "latency_ms": 450}
```

## Circuit Breaker

Resilience pattern for external service calls:

```python
from cognitia.resilience import CircuitBreaker

cb = CircuitBreaker(failure_threshold=3, recovery_timeout_s=60)

if cb.can_execute():
    try:
        result = await call_mcp_server()
        cb.record_success()
    except Exception:
        cb.record_failure()
        # After 3 failures, circuit opens for 60s
```

States: `closed` (normal) -> `open` (blocking) -> `half_open` (testing recovery).

## Context Builder

Token-budget-aware system prompt assembly:

```python
from cognitia.context import DefaultContextBuilder, ContextInput, ContextBudget

builder = DefaultContextBuilder(prompts_dir="./prompts")

inp = ContextInput(
    user_id="u1",
    topic_id="t1",
    role_id="coach",
    user_text="Help me save money",
    active_skill_ids=["finuslugi"],
    budget=ContextBudget(total_tokens=8000),
)

built = await builder.build(
    inp,
    user_profile=profile_pack,  # ContextPack(priority=6)
    active_goal=goal_pack,      # ContextPack(priority=2)
)

print(built.system_prompt)    # assembled prompt
print(built.prompt_hash)      # SHA256 hash (16 chars)
print(built.truncated_packs)  # which packs were cut by budget
```

### Priority overflow

When the budget is exceeded, packs are dropped from lowest to highest priority:

| Priority | Pack |
|----------|------|
| 0 | Guardrails |
| 1 | Role instruction |
| 2 | Active goals |
| 3 | Phase state |
| 4 | Tool hints / catalog |
| 5 | Memory recall / summary |
| 6 | User profile |

Guardrails are never dropped.

## Session Management

Manage multiple concurrent sessions:

```python
from cognitia.session import InMemorySessionManager, SessionKey

manager = InMemorySessionManager()

# Register a session
manager.register(session_state)

# Get session by key
state = manager.get(SessionKey("user_1", "topic_1"))

# Stream a reply
async for event in manager.stream_reply(key, "Hello"):
    print(event.type, event.text)
```

### Session rehydration

Restore session state after restart:

```python
from cognitia.session import DefaultSessionRehydrator

rehydrator = DefaultSessionRehydrator(
    messages=memory,
    summaries=memory,
    goals=memory,
    sessions=memory,
    phases=memory,
)

payload = await rehydrator.build_rehydration_payload(turn_context)
# Contains: role_id, active_skill_ids, prompt_hash,
#           summary, last_messages, goal, phase_state
```

## Role Routing

Automatic role switching based on user message keywords:

```python
from cognitia.routing import KeywordRoleRouter

router = KeywordRoleRouter(
    default_role="coach",
    keyword_map={
        "deposit_advisor": ["deposit", "savings account"],
        "credit_advisor": ["credit", "loan", "mortgage"],
    },
)

role = router.resolve("I want to open a savings account")  # "deposit_advisor"
role = router.resolve("Hello")                              # "coach"
role = router.resolve("...", explicit_role="coach")          # "coach" (explicit wins)
```

### YAML configuration

```yaml
# role_router.yaml
default_role: coach
roles:
  deposit_advisor:
    keywords: [deposit, savings]
  credit_advisor:
    keywords: [credit, loan]
```

```python
from cognitia.config import load_role_router_config

config = load_role_router_config("./prompts/role_router.yaml")
router = KeywordRoleRouter(
    default_role=config.default_role,
    keyword_map=config.keyword_map,
)
```

## Model Registry

Multi-provider model resolution with aliases:

```python
from cognitia.runtime import ModelRegistry, get_registry

registry = get_registry()

# Resolve aliases
registry.resolve("sonnet")  # "claude-sonnet-4-20250514"
registry.resolve("gpt-4o")  # "gpt-4o"
registry.resolve("gemini")  # "gemini-2.5-pro"

# Get provider
registry.get_provider("claude-sonnet-4-20250514")  # "anthropic"
registry.get_provider("gpt-4o")                     # "openai"
```

Models are defined in `cognitia/runtime/models.yaml` and support Anthropic, OpenAI, Google, and DeepSeek.

## Commands

Register custom slash commands:

```python
from cognitia.commands import CommandRegistry

registry = CommandRegistry()

registry.register(
    name="help",
    handler=my_help_handler,
    aliases=["h", "?"],
    description="Show help",
)

# Dispatch
result = await registry.dispatch("/help", context)
```
