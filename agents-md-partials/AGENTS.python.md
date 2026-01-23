## Python

### Principles

1. **Use `uv run python`** - Always execute Python commands via `uv run python ...` to ensure consistent dependency management and virtual environment isolation.

2. **Type hints everywhere** - Use type annotations for function signatures and variables to improve code clarity and enable better static analysis.

3. **Prefer standard library** - Use Python's standard library when possible before reaching for third-party packages. This reduces dependencies and improves portability.

4. **Explicit over implicit** - Write clear, readable code that makes intent obvious. Avoid magic methods and metaprogramming unless there's a compelling reason.

### Progress Bars

Use `tqdm` for user-facing scripts or long-running processes to provide feedback.

To keep log statements above the progress bar (preventing visual conflicts):

```python
from tqdm import tqdm

for item in tqdm(items, desc="Processing"):
    # Use tqdm.write() instead of print() for log messages
    tqdm.write(f"Processing {item.name}")
    process(item)
```

For logging module integration:

```python
import logging
from tqdm import tqdm

# Redirect logging through tqdm
class TqdmLoggingHandler(logging.Handler):
    def emit(self, record):
        tqdm.write(self.format(record))

logging.basicConfig(handlers=[TqdmLoggingHandler()], level=logging.INFO)
```
