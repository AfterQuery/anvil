## Task 10 — Memory leaks in long-running worker

There is a worker process that leaks memory over time under realistic loads.
Detect the source of leaks and fix them so memory usage stabilizes.

Requirements:
1. Provide fixes that prevent unbounded memory growth in long runs.
2. Add tests that demonstrate memory usage patterns or expose common leak
   patterns (circular refs, caching without eviction, unclosed resources).
3. Keep API surface unchanged.
