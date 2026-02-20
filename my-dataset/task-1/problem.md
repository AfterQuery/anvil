## Task 1: Add user profile endpoint

Implement a GET /api/profile endpoint that returns the authenticated user's profile.

Requirements:
1. Add `get_profile` method to `UserService` interface (in `service.py`).
2. Implement `get_profile` in the concrete `userService` class to return a `User` or None.
3. Add a controller handler for `/api/profile` in `controller.py` that returns 401 if unauthenticated, 404 if user not found, else 200 with user data.
4. Ensure the route registration uses the existing `require_auth` helper.

Tests are structural and check for method and route presence.