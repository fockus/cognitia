# Cognitia has been renamed to Swarmline

This project has moved to **[github.com/fockus/swarmline](https://github.com/fockus/swarmline)**.

## Migration

```bash
pip uninstall cognitia
pip install swarmline
```

Update your imports:

```python
# Before
from cognitia import Agent, AgentConfig

# After
from swarmline import Agent, AgentConfig
```

## Backward compatibility

`pip install cognitia>=1.5.0` will automatically install `swarmline` and re-export everything with a `DeprecationWarning`. This is a temporary bridge — please migrate to `swarmline` directly.

## Links

- **New repo**: [github.com/fockus/swarmline](https://github.com/fockus/swarmline)
- **PyPI**: [pypi.org/project/swarmline](https://pypi.org/project/swarmline/)
- **Docs**: [fockus.github.io/swarmline](https://fockus.github.io/swarmline/)
