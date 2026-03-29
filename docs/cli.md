# CLI Reference

Command-line interface for Cognitia agent infrastructure. Provides direct access to memory, plans, team coordination, agent management, and code execution.

## Installation

```bash
pip install cognitia[code-agent]
```

## Usage

```bash
cognitia [OPTIONS] COMMAND [ARGS]
```

## Global Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--format` | `auto`, `json`, `text` | `auto` | Output format. `auto` uses JSON when piped, text in terminal |
| `--help` | | | Show help and exit |

## Commands

### memory

Manage agent memory: facts, messages, and summaries.

```bash
# Store a fact
cognitia memory upsert alice language Python
cognitia memory upsert alice project "cognitia" --topic-id dev

# Retrieve facts
cognitia memory get alice
cognitia memory get alice --topic-id dev

# Get recent messages from a conversation
cognitia memory messages alice session-1
cognitia memory messages alice session-1 --limit 20
```

| Subcommand | Arguments | Options | Description |
|------------|-----------|---------|-------------|
| `upsert` | `USER_ID` `KEY` `VALUE` | `--topic-id` | Store or update a fact |
| `get` | `USER_ID` | `--topic-id` | Get all facts for a user |
| `messages` | `USER_ID` `TOPIC_ID` | `--limit` (default: 10) | Get recent conversation messages |

### plan

Manage agent plans: create, approve, and track step progress.

```bash
# Create a plan with steps
cognitia plan create "Refactor auth module" \
  -s "Extract interface" \
  -s "Write contract tests" \
  -s "Implement new adapter" \
  -s "Update DI wiring"

# List plans
cognitia plan list
cognitia plan list --user-id alice --topic-id project-x

# Get a specific plan
cognitia plan get plan-a1b2c3d4

# Approve a draft plan
cognitia plan approve plan-a1b2c3d4
cognitia plan approve plan-a1b2c3d4 --approved-by "tech-lead"

# Update step status
cognitia plan step plan-a1b2c3d4 step-e5f6g7h8 --status completed --result "Interface extracted"
cognitia plan step plan-a1b2c3d4 step-i9j0k1l2 --status failed --result "Tests revealed contract drift"
```

| Subcommand | Arguments | Options | Description |
|------------|-----------|---------|-------------|
| `create` | `GOAL` | `-s`/`--steps` (repeatable, required), `--user-id`, `--topic-id` | Create a plan |
| `get` | `PLAN_ID` | | Load a plan by ID |
| `list` | | `--user-id`, `--topic-id` | List plans in namespace |
| `approve` | `PLAN_ID` | `--approved-by` (default: "user") | Approve a draft plan |
| `step` | `PLAN_ID` `STEP_ID` | `--status` (required: `in_progress`/`completed`/`failed`/`skipped`), `--result` | Update step status |

### team

Manage agent teams: register agents, create tasks, and coordinate work.

```bash
# Register an agent
cognitia team register dev-1 "Developer Agent" developer
cognitia team register qa-1 "QA Agent" tester --parent-id dev-1 --runtime thin

# List agents
cognitia team agents
cognitia team agents --role developer --status active

# Create a task
cognitia team task task-001 "Implement login endpoint" \
  --description "REST endpoint with JWT auth" \
  --priority HIGH \
  --assignee dev-1

# Claim next available task
cognitia team claim
cognitia team claim --assignee dev-1

# List tasks
cognitia team tasks
cognitia team tasks --status pending --priority HIGH
```

| Subcommand | Arguments | Options | Description |
|------------|-----------|---------|-------------|
| `register` | `ID` `NAME` `ROLE` | `--parent-id`, `--runtime` (default: "thin") | Register an agent |
| `agents` | | `--role`, `--status` | List registered agents |
| `task` | `ID` `TITLE` | `--description`, `--priority` (`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`), `--assignee` | Create a task |
| `claim` | | `--assignee` | Claim highest-priority available task |
| `tasks` | | `--status`, `--priority`, `--assignee` | List tasks with filters |

### agent

Manage LLM-powered agents. Requires an API key (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`).

```bash
# Create an agent
cognitia agent create --prompt "You are a Python expert" --model sonnet
cognitia agent create -p "You review code for security issues" -m sonnet --runtime thin --max-turns 5

# Query an agent
cognitia agent query agent-a1b2c3d4 "Review this function for SQL injection"

# List agents
cognitia agent list
```

| Subcommand | Arguments | Options | Description |
|------------|-----------|---------|-------------|
| `create` | | `-p`/`--prompt` (required), `-m`/`--model` (default: "sonnet"), `--runtime` (default: "thin"), `--max-turns` | Create an agent |
| `query` | `AGENT_ID` `PROMPT` | | Send a prompt to an agent |
| `list` | | | List all created agents |

### run

Execute Python code in an isolated subprocess.

```bash
cognitia run "print('hello world')"
cognitia run "import sys; print(sys.version)" --timeout 10
```

| Arguments | Options | Description |
|-----------|---------|-------------|
| `CODE` | `--timeout` (default: 30, seconds) | Execute Python code |

### mcp-serve

Start the Cognitia MCP server (STDIO transport). Equivalent to running `cognitia-mcp`.

```bash
cognitia mcp-serve
cognitia mcp-serve --mode headless
cognitia mcp-serve --mode full
```

| Options | Description |
|---------|-------------|
| `--mode` (`auto`/`headless`/`full`, default: "auto") | Server mode |

## Output Format

All commands return JSON with a uniform schema:

```json
{"ok": true, "data": {"key": "language", "action": "upserted"}}
```

```json
{"ok": false, "error": "Plan not found: plan-xyz"}
```

When `--format text` is used, the output is rendered as human-readable text. `--format auto` detects whether stdout is a terminal and chooses accordingly.

Commands exit with code 0 on success and code 2 when `ok` is `false`.
