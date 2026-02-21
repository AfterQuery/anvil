class UserService:
    """Abstract service API for user lookups.

    Implementations should provide `get_user` and `get_profile`.
    The tests and tasks reference these method names, so keep the API
    stable when refactoring.
    """

    def get_user(self, user_id: int):
        """Return a raw `User` object or None if not found."""
        raise NotImplementedError()

    def get_profile(self, user_id: int):
        """Return a serializable profile mapping for `user_id`, or None."""
        raise NotImplementedError()


class userService(UserService):
    """Simple in-memory `UserService` implementation used for testing.

    This class seeds a single example user (id=1) so structural checks
    and simple integration tests can run without external dependencies.
    """

    def __init__(self):
        # Private in-memory store mapping user_id -> User
        self._store = {}
        from .models import User

        # Seed a friendly example user to make the toy API usable.
        self._store[1] = User(1, "Alice", "alice@example.com")

    def get_user(self, user_id: int):
        """Return the stored `User` instance or None."""
        return self._store.get(user_id)

    def get_profile(self, user_id: int):
        """Return a simple dict representation of the user or None."""
        user = self.get_user(user_id)
        if user is None:
            return None
        return {"id": user.id, "name": user.name, "email": user.email}
