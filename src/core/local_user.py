LOCAL_USER_ID = "local"


def list_users() -> list[dict]:
    """Single-user mode: the app serves one local user."""
    return [{"user_id": LOCAL_USER_ID}]
