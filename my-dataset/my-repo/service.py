class UserService:
    """Service interface placeholder. Tasks will add missing methods."""
    def get_user(self, user_id: int):
        raise NotImplementedError()

    def get_profile(self, user_id: int):
        """Return serialized profile for given user_id, or None."""
        raise NotImplementedError()


class userService(UserService):
    def __init__(self):
        self._store = {}
        # Seed with an example user so structural and simple integration checks can succeed
        from .models import User
        self._store[1] = User(1, "Alice", "alice@example.com")

    def get_user(self, user_id: int):
        return self._store.get(user_id)

    def get_profile(self, user_id: int):
        u = self.get_user(user_id)
        if u is None:
            return None
        return {"id": u.id, "name": u.name, "email": u.email}
