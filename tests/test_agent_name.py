import pytest

from hermes_agent_manager.agent_name import AgentName
from hermes_agent_manager.errors import InstallError


def test_parses_a_profile_name() -> None:
    agent = AgentName.parse("my-agent")

    assert agent.profile_name == "my-agent"
    assert agent.container_name == "HA-my-agent"


@pytest.mark.parametrize("raw", ["", "-bad", ".bad", "has space", "has/slash"])
def test_rejects_invalid_names(raw: str) -> None:
    with pytest.raises(InstallError):
        AgentName.parse(raw)
