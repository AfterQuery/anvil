# Task 1: Add User Profile Endpoint

## Objective
Implement a GET `/api/profile` endpoint that returns the authenticated user's profile information. This task requires integrating multiple layers: the service (business logic), the controller (HTTP routing), and authentication middleware.

## Background
The application separates concerns between:
- **Service layer** (`service.py`): Business logic for data operations (get_user, get_profile)
- **Controller layer** (`controller.py`): HTTP route handlers and request/response mapping
- **Utility layer** (`utils.py`): Helper functions like `require_auth` for authentication

## Requirements

### 1. Extend the Service Interface
Add a `get_profile` method signature to the `UserService` abstract class in `service.py`:
- Method name: `get_profile`
- Parameters: `user_id: int`
- Return type: dict (serialized profile) or None

### 2. Implement the Service Method
Implement `get_profile` in the concrete `userService` class:
- Fetch the User object using the existing `get_user` method
- Return None if user is not found
- Return a dictionary with keys `id`, `name`, and `email` if user exists

### 3. Create the HTTP Route
Add a new route handler in `register_routes()` in `controller.py`:
- Route path: `/api/profile`
- HTTP method: GET
- Authentication: Use the `require_auth` utility to check request headers
- Response codes:
  - 401 Unauthorized if authentication fails
  - 404 Not Found if user does not exist
  - 200 OK with JSON profile data if successful

### 4. Wire Authentication and Data Retrieval
- Import and use `require_auth` from `utils` to validate the request
- Instantiate `userService()` and call `get_profile(1)` to fetch data
- Return the profile dict or appropriate error codes

## Expected Complexity
This task involves:
- Understanding service/controller separation
- Using helper utilities correctly
- Proper error handling (401, 404)
- Basic data serialization (User → dict)

## Tests
The evaluation includes structural tests that verify:
1. `get_profile` method exists in the `UserService` interface
2. `get_profile` is implemented in the `userService` concrete class
3. `/api/profile` route is registered and calls `get_profile`