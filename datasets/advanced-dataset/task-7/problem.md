## Task 7 — Secure plugin DI

Design and implement a dependency-injection mechanism for third-party plugins
that prevents untrusted code from gaining arbitrary access to internal
services. The system should:

1. Limit the surface area exposed to plugins (capability-based interface).
2. Validate and sandbox plugin inputs and outputs.
3. Provide clear policy enforcement and auditing hooks.

Include tests that assert the presence of capability checks and restricted
access patterns.
