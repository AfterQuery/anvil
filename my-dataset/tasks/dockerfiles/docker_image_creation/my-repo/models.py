class User:
    """Lightweight user model used by the example service.

    Attributes:
        id: Numeric user identifier.
        name: Human-readable display name.
        email: Contact email address.
    """

    def __init__(self, id: int, name: str, email: str):
        self.id: int = id
        self.name: str = name
        self.email: str = email
