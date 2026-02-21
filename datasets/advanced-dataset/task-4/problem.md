## Task 4 — Transactional migration tool

Implement a migration tool to perform schema or data migrations across
large datasets with safe rollback and progress tracking.

Requirements:
1. Support transactional migration semantics (idempotent, resumable).
2. Provide a dry-run mode and a progress checkpointing mechanism.
3. Handle partial failures and allow safe retries.

Add tests that simulate partial failures and verify data consistency.
