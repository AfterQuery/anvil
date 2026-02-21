def require_auth(headers: dict) -> bool:
    """Validate request headers for a simple auth token.

    This function is an intentionally small placeholder used by the example
    controller. It expects the header `Authorization: Token secret` and
    returns True when provided; otherwise False.

    Args:
        headers: Mapping-like object containing HTTP headers (case-sensitive).

    Returns:
        True if the expected token is present, False otherwise.
    """
    auth = headers.get("Authorization")
    return auth == "Token secret"
