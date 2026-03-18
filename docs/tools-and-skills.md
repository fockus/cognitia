# Tools & Skills

Cognitia provides two mechanisms for giving agents capabilities: **tools** (code-defined) and **skills** (declarative MCP).

## @tool Decorator

Define tools as async Python functions with automatic JSON Schema inference:

```python
from cognitia import tool

@tool(name="lookup_user", description="Look up user by email")
async def lookup_user(email: str) -> str:
    # Auto-inferred schema: {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]}
    user = await db.find_by_email(email)
    return f"Found: {user.name}" if user else "Not found"
```

### Type mapping

| Python | JSON Schema |
|--------|-------------|
| `str` | `"string"` |
| `int` | `"integer"` |
| `float` | `"number"` |
| `bool` | `"boolean"` |
| `T \| None = None` | not in `required` |

### Using tools with Agent

```python
from cognitia import Agent, AgentConfig

agent = Agent(AgentConfig(
    runtime="thin",
    tools=(lookup_user, another_tool),
))
```

### Handler contract

The `@tool` decorator handles the conversion between your natural Python function signature and the MCP protocol format automatically:

- Your handler: `async def fn(a: int, b: str) -> str`
- SDK expects: `handler({"a": 1, "b": "hello"}) -> {"content": [{"type": "text", "text": "result"}]}`

Cognitia's `_adapt_handler` bridges this gap transparently. If your handler raises an exception, it's caught and returned as an error in MCP format.

## MCP Skills (Declarative)

Skills are YAML-configured MCP server connections with tool allowlists:

```yaml
# skills/finuslugi/skill.yaml
skill_id: finuslugi
title: "Banking Products API"
mcp_servers:
  - name: finuslugi-server
    transport: url
    url: "https://api.example.com/mcp"
tool_include:
  - get_bank_deposits
  - get_bank_credits
intents: [deposits, credits]
```

Each skill can have an instruction file for the agent:

```markdown
# skills/finuslugi/INSTRUCTION.md
Use `get_bank_deposits` to search for deposit products.
Always specify amount and term in months.
```

### Loading skills

```python
from cognitia.skills import SkillRegistry
from cognitia.skills.loader import YamlSkillLoader

loader = YamlSkillLoader("./skills")
skills = loader.load_all()
registry = SkillRegistry(skills)

# Get MCP servers for active skills
servers = registry.get_mcp_servers_for_skills(["finuslugi"])

# Get tool allowlist
tools = registry.get_tool_allowlist(["finuslugi"])
# -> {"mcp__finuslugi__get_bank_deposits", "mcp__finuslugi__get_bank_credits"}
```

### Skill transports

| Transport | Config | Use Case |
|-----------|--------|----------|
| `url` | `url: "https://..."` | Remote MCP server (SSE) |
| `stdio` | `command: "python server.py"` | Local subprocess |
| `sse` | `url: "https://..."` | Server-Sent Events |

## Tool Policy

Default-deny policy controls which tools agents can use:

```python
from cognitia.policy import DefaultToolPolicy

policy = DefaultToolPolicy()

# Check if a tool is allowed
result = policy.can_use_tool(
    tool_name="mcp__finuslugi__get_deposits",
    input_data={"amount": 500000},
    state=policy_state,  # contains active_skill_ids, allowed_local_tools
)
```

### Always denied tools

These tools are blocked regardless of configuration:
`Bash`, `Read`, `Write`, `Edit`, `MultiEdit`, `Glob`, `Grep`, `LS`, `TodoRead`, `TodoWrite`, `WebFetch`, `WebSearch`.

### Allow rules

A tool is allowed if:
1. It matches an active skill's tool allowlist (`mcp__<skill>__<tool>`)
2. It's in the `allowed_local_tools` set
3. It's in the `allowed_system_tools` set (for web tools etc.)

## Tool ID Codec

MCP tools use a namespaced format: `mcp__<server>__<tool>`.

```python
from cognitia.policy import DefaultToolIdCodec

codec = DefaultToolIdCodec()
codec.encode("finuslugi", "get_deposits")     # "mcp__finuslugi__get_deposits"
codec.extract_server("mcp__finuslugi__get_deposits")  # "finuslugi"
codec.matches("mcp__finuslugi__get_deposits", "finuslugi")  # True
```

## Role-Skill Mapping

Map roles to their allowed skills and local tools:

```yaml
# role_skills.yaml
coach:
  mcp_skills: []
  local_tools: [calculate_goal_plan]

deposit_advisor:
  mcp_skills: [finuslugi, funds]
  local_tools: [calculate_goal_plan]
```

```python
from cognitia.config import YamlRoleSkillsLoader

loader = YamlRoleSkillsLoader("./prompts/role_skills.yaml")
skills = loader.get_skills("deposit_advisor")  # ["finuslugi", "funds"]
tools = loader.get_local_tools("deposit_advisor")  # ["calculate_goal_plan"]
```
