## Task 3 — API rate limiter hardening

There is a rate limiter that currently allows bypasses under certain timings.
Implement a robust token-bucket or leaky-bucket limiter that:

1. Correctly accounts for burst allowance and refill rates.
2. Is safe under concurrent requests from multiple worker processes.
3. Has clear configuration and defensive checks (negative rates, zero capacity).

Requirements:
- Add tests for boundary conditions and simulated concurrent bursts.
