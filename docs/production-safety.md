# Production Safety

Cognitia provides four complementary safety mechanisms for production deployments: **cost budgets**, **guardrails**, **input filters**, and **retry/fallback policies**. All are opt-in via `RuntimeConfig` — disabled by default for zero overhead.

## Cost Budget Tracking

Track accumulated LLM costs and enforce spending limits.

```python
from cognitia.runtime.cost import CostBudget
from cognitia.runtime.types import RuntimeConfig

config = RuntimeConfig(
    runtime_name="thin",
    cost_budget=CostBudget(
        max_cost_usd=5.0,           # USD spending cap
        max_total_tokens=1_000_000,  # token cap (optional)
        action_on_exceed="error",    # "error" (stop) or "warn" (continue)
    ),
)
```

### How It Works

- ThinRuntime creates a `CostTracker` at startup and records usage after each LLM call
- Costs are computed using bundled `pricing.json` (updated with major model releases)
- Unknown models fall back to `_default` pricing — no crashes on new models
- When exceeded: emits `RuntimeEvent` with `kind="budget_exceeded"` (error mode) or continues with warning
- Final event includes `total_cost_usd` when budget tracking is active

### Bundled Pricing

| Model | Input $/1M tokens | Output $/1M tokens |
|-------|-------------------|-------------------|
| claude-sonnet-4-20250514 | 3.00 | 15.00 |
| gpt-4o | 2.50 | 10.00 |
| gpt-4o-mini | 0.15 | 0.60 |
| gemini-2.0-flash | 0.10 | 0.40 |
| `_default` | 3.00 | 15.00 |

### Programmatic Access

```python
from cognitia.runtime.cost import CostTracker, load_pricing

tracker = CostTracker(budget=budget, pricing=load_pricing())
tracker.record("gpt-4o", input_tokens=1000, output_tokens=500)

print(tracker.total_cost_usd)    # accumulated cost
print(tracker.total_tokens)      # accumulated tokens
print(tracker.check_budget())    # "ok" | "warning" | "exceeded"
tracker.reset()                  # zero all counters
```

---

## Guardrails

Pre- and post-LLM content checks. Input guardrails run before the LLM call; output guardrails run after. A failed guardrail emits an error event with `kind="guardrail_tripwire"`.

```python
from cognitia.guardrails import (
    ContentLengthGuardrail,
    RegexGuardrail,
    CallerAllowlistGuardrail,
)
from cognitia.runtime.types import RuntimeConfig

config = RuntimeConfig(
    runtime_name="thin",
    input_guardrails=[
        ContentLengthGuardrail(max_length=8000),
        RegexGuardrail(patterns=[r"ignore previous instructions"]),
    ],
    output_guardrails=[
        RegexGuardrail(
            patterns=[r"SECRET_\d+"],
            reason="Sensitive data leaked in response",
        ),
    ],
)
```

### Built-in Guardrails

| Guardrail | Description |
|-----------|-------------|
| `ContentLengthGuardrail` | Rejects text longer than `max_length` characters (default: 100,000) |
| `RegexGuardrail` | Rejects text matching any of the given regex `patterns` |
| `CallerAllowlistGuardrail` | Rejects requests from `session_id` not in the allowlist |

### Custom Guardrails

Implement the `Guardrail` protocol:

```python
from cognitia.guardrails import GuardrailContext, GuardrailResult

class ToxicityGuardrail:
    async def check(self, ctx: GuardrailContext, text: str) -> GuardrailResult:
        if is_toxic(text):
            return GuardrailResult(passed=False, reason="Toxic content detected")
        return GuardrailResult(passed=True)
```

### Execution Model

- All guardrails run in parallel via `asyncio.gather` — N guardrails don't add linear latency
- First failure stops execution and emits an error event
- `tripwire=True` in `GuardrailResult` marks a hard, non-recoverable failure

---

## Input Filters

Transform messages and system prompt before each LLM call. Filters are applied sequentially in list order.

```python
from cognitia.input_filters import MaxTokensFilter, SystemPromptInjector
from cognitia.runtime.types import RuntimeConfig

config = RuntimeConfig(
    runtime_name="thin",
    input_filters=[
        SystemPromptInjector(
            extra_text="Always reply in English.",
            position="prepend",  # or "append"
        ),
        MaxTokensFilter(max_tokens=64_000),
    ],
)
```

### Built-in Filters

| Filter | Description |
|--------|-------------|
| `MaxTokensFilter` | Trims older messages to fit within `max_tokens` budget. Always preserves system prompt and the last message. Token estimation: `len(text) / chars_per_token` (default 4.0). |
| `SystemPromptInjector` | Prepends or appends text to the system prompt. |

### Custom Filters

Implement the `InputFilter` protocol:

```python
class RedactFilter:
    async def filter(self, messages, system_prompt):
        cleaned = [redact_pii(m) for m in messages]
        return cleaned, system_prompt
```

---

## Retry / Fallback Policy

Automatic retry with exponential backoff when LLM calls fail.

```python
from cognitia.retry import ExponentialBackoff
from cognitia.runtime.types import RuntimeConfig

config = RuntimeConfig(
    runtime_name="thin",
    retry_policy=ExponentialBackoff(
        max_retries=3,       # up to 3 retries (4 total attempts)
        base_delay=1.0,      # seconds
        max_delay=60.0,      # cap
        jitter=True,         # random factor 0.5-1.5x
    ),
)
```

### Delay Formula

```
delay = min(base_delay * 2^attempt, max_delay) * uniform(0.5, 1.5)
```

### Model Fallback Chain

Switch to a backup model when the primary fails:

```python
from cognitia.retry import ModelFallbackChain

chain = ModelFallbackChain(models=["gpt-4o", "claude-sonnet-4-20250514", "gemini-2.0-flash"])
next_model = chain.next_model("gpt-4o")  # "claude-sonnet-4-20250514"
```

### Custom Retry Policies

Implement the `RetryPolicy` protocol:

```python
class MyRetryPolicy:
    def should_retry(self, error: Exception, attempt: int) -> tuple[bool, float]:
        if attempt < 2 and "rate_limit" in str(error):
            return True, 5.0  # retry after 5 seconds
        return False, 0.0
```

---

## Data Flow

The complete request pipeline with all safety mechanisms:

```
User Input
    │
    ▼
Input Filters (sequential: SystemPromptInjector → MaxTokensFilter → RagInputFilter)
    │
    ▼
Input Guardrails (parallel, asyncio.gather)
    │  fail → error event, kind="guardrail_tripwire"
    ▼  pass
LLM Call
    │  error → RetryPolicy.should_retry → retry loop or error event
    ▼  success
Output Guardrails (parallel)
    │  fail → error event, kind="guardrail_tripwire"
    ▼  pass
CostTracker.record → check_budget
    │  exceeded → budget_exceeded event (if action="error")
    ▼  ok
Final RuntimeEvent
```
