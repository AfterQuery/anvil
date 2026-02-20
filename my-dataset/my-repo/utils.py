def require_auth(headers: dict) -> bool:
    """Simple auth check placeholder: expects Authorization header 'Token secret'."""
    auth = headers.get('Authorization')
    return auth == 'Token secret'
