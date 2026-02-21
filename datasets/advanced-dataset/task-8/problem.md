## Task 8 — Streaming CSV/JSON converter

Implement a high-throughput converter that transforms large CSV streams into
JSON objects and vice versa without loading the entire file into memory. The
converter should:

1. Accept arbitrary column orders and optional headers.
2. Support configurable chunk sizes and backpressure.
3. Produce deterministic ordering for stable downstream processing.

Tests should include malformed rows, huge streams, and header mismatches.
