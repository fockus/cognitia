# Cognitia Examples

Standalone runnable examples demonstrating Cognitia features.
All examples use mock data -- no API keys required.

## Running

```bash
pip install -e ".[dev,all]"
python examples/01_structured_output.py
```

## Examples

| # | File | Feature | Key Imports |
|---|------|---------|-------------|
| 01 | `01_structured_output.py` | Pydantic structured output | `validate_structured_output`, `extract_pydantic_schema` |
| 02 | `02_tool_decorator.py` | `@tool` decorator with type hints | `tool`, `ToolDefinition` |
| 03 | `03_guardrails.py` | Input/output safety checks | `ContentLengthGuardrail`, `RegexGuardrail` |
| 04 | `04_cost_budget.py` | Cost budget tracking | `CostBudget`, `CostTracker`, `ModelPricing` |
| 05 | `05_retry_fallback.py` | Retry and model fallback | `ExponentialBackoff`, `ModelFallbackChain` |
| 06 | `06_sessions.py` | Session persistence + scopes | `InMemorySessionBackend`, `MemoryScope`, `scoped_key` |
| 07 | `07_event_bus_tracing.py` | Pub-sub events + tracing | `InMemoryEventBus`, `NoopTracer`, `TracingSubscriber` |
| 08 | `08_ui_projection.py` | Event stream to UI state | `ChatProjection`, `project_stream` |
| 09 | `09_rag.py` | Retrieval-augmented generation | `SimpleRetriever`, `RagInputFilter`, `Document` |
