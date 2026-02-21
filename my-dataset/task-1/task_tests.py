from pathlib import Path
import os

BASE = os.environ.get("ANVIL_APP_PATH", "/workspaces/anvil/my-dataset/my-repo")

def test_get_profile_in_interface():
    """Verify that the UserService interface exposes a get_profile method signature.
    
    The public API contract requires a `get_profile` method on the UserService
    abstract class so that implementations have a consistent interface. This test
    checks that the method name appears in the service.py file, indicating the
    interface contract is properly defined for agents to implement.
    """
    content = Path(f"{BASE}/service.py").read_text()
    assert "get_profile" in content, "get_profile not in interface"

def test_get_profile_implemented():
    """Verify that get_profile is implemented as a concrete method in userService.
    
    The userService class (concrete implementation of UserService) must provide
    a working implementation of get_profile that returns user profile data or None.
    This test confirms the method definition exists in the concrete class,
    enabling agents to call it during task execution to fetch user profiles.
    """
    content = Path(f"{BASE}/service.py").read_text()
    assert "def get_profile" in content or "def get_profile(self" in content

def test_profile_route_exists():
    """Verify that the /api/profile endpoint exists and is wired to get_profile.
    
    The HTTP layer (controller) must register a route at /api/profile that calls
    the service's get_profile method. This test confirms both the route path and
    the service integration are present in the codebase, ensuring agents can make
    requests to the endpoint and receive data from the business logic layer.
    """
    content = Path(f"{BASE}/controller.py").read_text()
    assert "/api/profile" in content and "get_profile" in content

def test_get_profile_returns_dict():
    """Verify that get_profile returns a dictionary for valid user IDs.
    
    The get_profile method must return a dict-like object when called with a
    valid user ID. This ensures the method has a proper implementation that returns
    structured data suitable for serialization to JSON in HTTP responses.
    """
    import sys
    import os
    
    # Add the parent directory to sys.path so imports work
    parent_dir = os.path.dirname(BASE)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Get the repo package name
    repo_name = os.path.basename(BASE)
    
    # Import via __import__
    service_module = __import__(f"{repo_name}.service", fromlist=["userService"])
    userService = service_module.userService
    
    svc = userService()
    result = svc.get_profile(1)
    assert isinstance(result, dict), "get_profile must return a dictionary"

def test_get_profile_contains_required_fields():
    """Verify that get_profile returns a dict with id, name, and email fields.
    
    The profile dict must contain the required fields (id, name, email) to maintain
    the API contract expected by clients. This test ensures agents implement a
    properly structured response with all necessary user information.
    """
    import sys
    import os
    
    # Add the parent directory to sys.path so imports work
    parent_dir = os.path.dirname(BASE)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Get the repo package name
    repo_name = os.path.basename(BASE)
    
    # Import via __import__
    service_module = __import__(f"{repo_name}.service", fromlist=["userService"])
    userService = service_module.userService
    
    svc = userService()
    result = svc.get_profile(1)
    assert isinstance(result, dict), "get_profile must return a dict"
    assert "id" in result, "profile dict must contain 'id' field"
    assert "name" in result, "profile dict must contain 'name' field"
    assert "email" in result, "profile dict must contain 'email' field"

def test_get_profile_returns_none_for_missing_user():
    """Verify that get_profile returns None when user does not exist.
    
    When called with an invalid user ID, get_profile should return None rather
    than raising an exception. This allows controllers to handle missing users
    gracefully with appropriate HTTP status codes (404, etc).
    """
    import sys
    import os
    
    # Add the parent directory to sys.path so imports work
    parent_dir = os.path.dirname(BASE)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Get the repo package name
    repo_name = os.path.basename(BASE)
    
    # Import via __import__
    service_module = __import__(f"{repo_name}.service", fromlist=["userService"])
    userService = service_module.userService
    
    svc = userService()
    result = svc.get_profile(99999)
    assert result is None, "get_profile must return None for non-existent users"
