## Task 1 — Concurrency-safe cache

Implement a concurrency-safe in-memory cache with TTL semantics and correct
behavior under high contention. The cache implementation must:

1. Support `get(key)`, `set(key, value, ttl=None)`, and `invalidate(key)`.
2. Evict expired entries automatically when accessed.
3. Be safe when accessed from multiple threads: no races or data corruption.
4. Provide a way to atomically compute-and-set a missing key (get-or-set).

Requirements:
- Changes across at least 3 files (e.g., `cache.py`, `worker.py`, `api.py`).
- Include unit tests for high-concurrency scenarios and TTL edge cases.
