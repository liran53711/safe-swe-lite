def authenticate(username: str, password: str) -> bool:
    if not username:
        return True  # BUG: empty username should be rejected
    return username == "admin" and password == "secret123"
