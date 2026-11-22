import pytest

from hermes_agent_manager.agent_name import AgentName
from hermes_agent_manager.errors import InstallError


def test_parses_a_profile_name_with_site() -> None:
    agent = AgentName.parse("stm", "venus.localhost")

    assert agent.profile_name == "stm"
    assert agent.site_slug == "venus"
    assert agent.container_name == "HA-venus-stm"
    assert agent.volume_name == "ham-venus-stm"
    assert agent.hermes_alias == "venus-stm"
    assert agent.gateway_url == "http://venus-stm:9119"


def test_site_slug_strips_localhost_suffix() -> None:
    assert AgentName.parse("a", "fxl16.localhost").site_slug == "fxl16"
    assert AgentName.parse("a", "a.b.localhost").site_slug == "a-b"


@pytest.mark.parametrize("raw", ["", "-bad", ".bad", "has space", "has/slash"])
def test_rejects_invalid_names(raw: str) -> None:
    with pytest.raises(InstallError):
        AgentName.parse(raw)
