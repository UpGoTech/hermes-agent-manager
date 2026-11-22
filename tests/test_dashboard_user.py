import pytest

from hermes_agent_manager.dashboard_user import parse_dashboard_user
from hermes_agent_manager.errors import InstallError


def test_parses_explicit_user() -> None:
    assert parse_dashboard_user("alice", interactive=False) == "alice"


def test_requires_user_when_non_interactive() -> None:
    with pytest.raises(InstallError, match="--user"):
        parse_dashboard_user(None, interactive=False)


def test_prompts_when_interactive(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: " bob ")
    assert parse_dashboard_user(None, interactive=True) == "bob"


@pytest.mark.parametrize("raw", ["", "-bad", "has space"])
def test_rejects_invalid_users(raw: str) -> None:
    with pytest.raises(InstallError, match="Dashboard username"):
        parse_dashboard_user(raw, interactive=False)
