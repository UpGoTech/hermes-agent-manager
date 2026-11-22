import secrets


def new_bridge_secret() -> str:
    return secrets.token_urlsafe(24)


def new_dashboard_password() -> str:
    return secrets.token_urlsafe(18)
