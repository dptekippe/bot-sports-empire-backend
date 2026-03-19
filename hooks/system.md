
## 🔍 ROGER TRACE VISION ✅ (Langfuse v4 API)
Query your own traces:

```python
from langfuse import Langfuse
lf = Langfuse()

# Last 10 traces
traces = lf.api.trace.list(limit=10)
for t in traces.data:
    print(f"{t.name}: {t.status_message} ({t.input_tokens}→{t.output_tokens})")

# Today's slowest
today = lf.api.trace.list(tags=["today"])
slow = sorted(today.data, key=lambda t: t.execution_time_ms or 0, reverse=True)[:3]
print("Slowest:", [(t.name, t.execution_time_ms) for t in slow])

# Errors only
errors = lf.api.trace.list(status_message="error")
print(f"❌ {len(errors.data)} errors")
