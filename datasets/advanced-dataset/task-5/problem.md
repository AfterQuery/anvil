## Task 5 — Deterministic serialization and schema evolution

Implement a deterministic serializer/deserializer that supports evolving
schemas. The system should:

1. Produce deterministic bytes for the same logical object across runs.
2. Allow schema evolution with backward compatibility (optional fields,
   versioning headers).
3. Provide validation and clear error messages on mismatch.

Tests should include older/newer schema round-trips and malformed data.
