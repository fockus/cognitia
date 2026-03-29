# Claude Code Integration

Step-by-step guide for using Cognitia's MCP server with Claude Code. This gives Claude persistent memory, structured planning, team coordination, and code execution across conversations.

## 1. Install Cognitia

```bash
pip install cognitia[code-agent]
```

Verify the entry point is available:

```bash
cognitia-mcp --help
```

If you use a virtual environment, make sure it is activated or that `cognitia-mcp` is on your `PATH`.

## 2. Configure MCP Server

Add Cognitia to your Claude Code MCP settings. Choose project-level or global scope.

**Project-level** (`.claude/settings.json` in your repo root):

```json
{
  "mcpServers": {
    "cognitia": {
      "command": "cognitia-mcp",
      "args": ["auto"]
    }
  }
}
```

**Global** (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "cognitia": {
      "command": "cognitia-mcp",
      "args": ["auto"]
    }
  }
}
```

If `cognitia-mcp` is installed in a virtual environment, use the full path:

```json
{
  "mcpServers": {
    "cognitia": {
      "command": "/path/to/venv/bin/cognitia-mcp",
      "args": ["auto"]
    }
  }
}
```

## 3. Set API Keys (Optional)

For full mode with agent creation/querying, export your API key before starting Claude Code:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Without an API key, the server runs in headless mode (17 tools). With an API key, it runs in full mode (20 tools, adding agent creation and querying).

## 4. Install SKILL.md (Optional)

If you have a Cognitia `SKILL.md` file that teaches Claude Code how to use the tools effectively, place it in your project:

```bash
cp path/to/cognitia-skill.md .claude/skills/cognitia.md
```

Claude Code reads skill files automatically and uses them to understand when and how to call the MCP tools.

## 5. Verify Connection

Start Claude Code in your project directory. Ask it to check the Cognitia server status:

> Check Cognitia MCP server status

Claude should call `cognitia_status` and return the current mode and agent count.

## 6. Example Workflows

### Persistent Memory Across Conversations

Store project facts that persist for the lifetime of the MCP server session:

> Remember that this project uses PostgreSQL 16 and Python 3.12

Claude calls `cognitia_memory_upsert_fact` with key-value pairs. In a later message:

> What database does this project use?

Claude calls `cognitia_memory_get_facts` and retrieves the stored facts.

### Structured Planning

Create and track multi-step plans:

> Create a plan to migrate from SQLite to PostgreSQL with these steps:
> 1. Add asyncpg dependency
> 2. Implement PostgreSQL adapter
> 3. Write integration tests
> 4. Update DI configuration
> 5. Run migration script

Claude calls `cognitia_plan_create`, then updates each step's status with `cognitia_plan_update_step` as work progresses.

### Team Coordination

When running multiple Claude Code agents (e.g., via Claude Agent SDK):

> Register yourself as the backend developer agent

Claude calls `cognitia_team_register_agent`. The lead agent can then create tasks with `cognitia_team_create_task`, and worker agents claim them with `cognitia_team_claim_task`.

### Code Execution

Run quick scripts without leaving the conversation:

> Execute this Python code: import platform; print(platform.python_version())

Claude calls `cognitia_exec_code` and returns the output.

## Troubleshooting

**Tools not appearing in Claude Code**
Restart Claude Code after editing the settings file. Check that `cognitia-mcp` is on your PATH by running `which cognitia-mcp` in the same shell environment.

**"FastMCP is required" error**
The `[code-agent]` extra was not installed. Run `pip install cognitia[code-agent]` again.

**State resets between Claude Code sessions**
Memory and plans are stored in-memory for the lifetime of the MCP server process. When Claude Code restarts, it starts a new server process. For persistent storage across sessions, use the SQLite or PostgreSQL memory backends via the Cognitia Python API.
