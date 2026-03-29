# Agent Evaluation

Cognitia includes a built-in evaluation framework for measuring agent quality across multiple dimensions.

## Quick Start

```python
from cognitia.eval.runner import EvalRunner
from cognitia.eval.scorers import ContainsScorer, ExactMatchScorer
from cognitia.eval.reporters import ConsoleReporter
from cognitia.eval.types import EvalCase

suite = [
    EvalCase(id="geo-1", input="Capital of France?", expected="Paris"),
    EvalCase(id="math-1", input="2+2?", expected="4"),
]

runner = EvalRunner()
report = await runner.run(agent=my_agent, suite=suite, scorers=[
    ExactMatchScorer(),
    ContainsScorer(),
])

print(ConsoleReporter().format(report))
```

## Concepts

### EvalCase

A single test case with input, expected output, and optional context:

```python
EvalCase(
    id="unique-id",
    input="user prompt",
    expected="expected answer or substring",
    context={"latency_ms": 200, "cost_usd": 0.003},  # metadata for scorers
    tags=("category", "difficulty"),
)
```

### Scorers

Scorers evaluate agent output and return a `ScorerResult` (score 0.0-1.0 + reason).

| Scorer | What it checks |
|--------|---------------|
| `ExactMatchScorer` | `output == expected` (optional case-insensitive) |
| `ContainsScorer` | `expected in output` |
| `RegexScorer` | Regex pattern match on output |
| `LatencyScorer` | Response time under threshold |
| `CostScorer` | Token cost under budget |

### EvalReport

Aggregated results with statistics:

```python
report.total      # number of cases
report.passed     # cases where all scores >= 0.5
report.failed     # total - passed
report.pass_rate  # passed / total
report.mean_score # average across all cases

# Per-scorer stats
report.scorer_stats("contains")  # {"mean": 0.85, "min": 0.0, "max": 1.0, "p50": 1.0, "p95": 1.0}
```

## Reporters

### Console

```python
from cognitia.eval.reporters import ConsoleReporter
print(ConsoleReporter().format(report))
```

### JSON (for CI/CD)

```python
from cognitia.eval.reporters import JsonReporter
json_str = JsonReporter(indent=2).format(report)
```

## Custom Scorers

Implement the `Scorer` protocol:

```python
from cognitia.eval.types import EvalCase, Scorer, ScorerResult

class MyCustomScorer:
    @property
    def name(self) -> str:
        return "custom"

    async def score(self, case: EvalCase, output: str) -> ScorerResult:
        # Your scoring logic
        is_good = "thank you" in output.lower()
        return ScorerResult(
            score=1.0 if is_good else 0.0,
            reason="polite" if is_good else "impolite",
        )
```

## Example

See [`examples/32_agent_evaluation.py`](https://github.com/fockus/cognitia/blob/main/examples/32_agent_evaluation.py) for a complete runnable example.
