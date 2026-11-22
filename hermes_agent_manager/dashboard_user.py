import re

from hermes_agent_manager.errors import InstallError

_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def parse_dashboard_user(raw: str | None, interactive: bool) -> str:
    if raw is not None:
        return _validate(raw.strip())
    if not interactive:
        raise InstallError("Pass --user <name> for the Hermes dashboard username.")
    entered = input("Dashboard username: ").strip()
    return _validate(entered)


def _validate(value: str) -> str:
    if not value or _PATTERN.fullmatch(value) is None:
        raise InstallError(
            "Dashboard username must start with a letter or digit and contain only "
            "letters, digits, dots, underscores, and hyphens."
        )
    return value
