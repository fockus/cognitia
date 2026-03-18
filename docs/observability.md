# Observability

Lightweight event bus and structured tracing for runtime instrumentation.

## Event Bus

A pub-sub event bus for internal runtime events. Subscribers (tracing, metrics, UI) receive events without coupling to the runtime.

```python
from cognitia.observability.event_bus import InMemoryEventBus
from cognitia.runtime.types import RuntimeConfig

bus = InMemoryEventBus()

# Subscribe to events
metrics = []
bus.subscribe("llm_call_end", lambda data: metrics.append(data))

# Wire into runtime
config = RuntimeConfig(runtime_name="thin", event_bus=bus)
```

### Automatic Events

When `event_bus` is set in `RuntimeConfig`, ThinRuntime emits these events automatically:

| Event | When | Data fields |
|-------|------|-------------|
| `llm_call_start` | Before LLM request | `model` |
| `llm_call_end` | After LLM response | `model`, `error` (if failed) |
| `tool_call_start` | Before tool execution | `name`, `correlation_id` |
| `tool_call_end` | After tool execution | `name`, `ok`, `correlation_id` |

### EventBus Protocol

```python
class EventBus(Protocol):
    def subscribe(self, event_type: str, callback) -> str: ...     # returns subscription ID
    def unsubscribe(self, subscription_id: str) -> None: ...
    async def emit(self, event_type: str, data: dict) -> None: ...
```

- Supports both sync and async callbacks
- Errors in callbacks are caught and ignored (fire-and-forget semantics)
- Unsubscribing a non-existent ID is a no-op

---

## Tracing

Span-based structured tracing via the `Tracer` protocol. `TracingSubscriber` bridges EventBus events to Tracer spans automatically.

```python
from cognitia.observability.event_bus import InMemoryEventBus
from cognitia.observability.tracer import ConsoleTracer, TracingSubscriber
from cognitia.runtime.types import RuntimeConfig

bus = InMemoryEventBus()
tracer = ConsoleTracer()

# Bridge: EventBus events → Tracer spans
subscriber = TracingSubscriber(bus, tracer)
subscriber.attach()

config = RuntimeConfig(runtime_name="thin", event_bus=bus, tracer=tracer)

# After execution, inspect spans:
# tracer._spans contains all recorded spans with timing
subscriber.detach()
```

### Built-in Tracers

| Tracer | Description |
|--------|-------------|
| `NoopTracer` | Zero-overhead stub for production without tracing |
| `ConsoleTracer` | Logs spans via `structlog` with `duration_ms` timing |

### Tracer Protocol

```python
class Tracer(Protocol):
    def start_span(self, name: str, attrs: dict | None = None) -> str: ...  # span_id
    def end_span(self, span_id: str) -> None: ...
    def add_event(self, span_id: str, name: str, attrs: dict | None = None) -> None: ...
```

### Custom Tracers

Bridge to OpenTelemetry, Datadog, or any observability platform:

```python
from opentelemetry import trace

class OTelTracer:
    def __init__(self):
        self._tracer = trace.get_tracer("cognitia")
        self._spans = {}

    def start_span(self, name, attrs=None):
        span = self._tracer.start_span(name, attributes=attrs or {})
        span_id = f"otel_{id(span)}"
        self._spans[span_id] = span
        return span_id

    def end_span(self, span_id):
        if span_id in self._spans:
            self._spans.pop(span_id).end()

    def add_event(self, span_id, name, attrs=None):
        if span_id in self._spans:
            self._spans[span_id].add_event(name, attributes=attrs or {})
```

### TracingSubscriber Lifecycle

```python
subscriber = TracingSubscriber(bus, tracer)
subscriber.attach()   # subscribes to llm_call_start/end, tool_call_start/end
# ... runtime execution ...
subscriber.detach()   # removes all subscriptions
```

`attach()` / `detach()` provide explicit lifecycle control — the subscriber can be reused across multiple runs.

---

## Combining with Other Features

Event bus integrates naturally with other Cognitia features:

```python
from cognitia.runtime.cost import CostBudget
from cognitia.observability.event_bus import InMemoryEventBus
from cognitia.observability.tracer import ConsoleTracer, TracingSubscriber

bus = InMemoryEventBus()
tracer = ConsoleTracer()
TracingSubscriber(bus, tracer).attach()

config = RuntimeConfig(
    runtime_name="thin",
    event_bus=bus,
    tracer=tracer,
    cost_budget=CostBudget(max_cost_usd=10.0),
)
# Cost events, tool calls, and LLM calls are all traced automatically
```
