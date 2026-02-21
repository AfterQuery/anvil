## Task 2 — Incremental indexer

Implement an incremental indexer over a dataset of text documents that:

1. Can update the index with diffs (added/removed/modified docs) without
   rebuilding the entire index.
2. Supports concurrent updates and provides a deterministic merge order.
3. Exposes a simple query API for prefix and substring matches.

Requirements:
- Changes across at least 3 files (indexer, persistence, CLI).
- Provide tests for correctness after sequences of diffs and rollback.
