## Task 9 — Idempotent webhook processing

Build an idempotent webhook handler that ensures each inbound event is
processed exactly once, even under retries and parallel delivery.

Requirements:
1. Provide durable deduplication (idempotency keys) and safe retries.
2. Ensure ordering per source (if required) without blocking other sources.
3. Provide clear failure semantics and requeueing behavior.

Tests should simulate duplicate deliveries and concurrent processing.
