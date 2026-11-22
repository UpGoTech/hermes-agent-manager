from hermes_agent_manager.agent_name import AgentName
from hermes_agent_manager.dashboard_port import host_dashboard_port


def test_host_port_is_stable_per_identity() -> None:
    agent = AgentName.parse("stm", "venus.localhost")
    assert host_dashboard_port(agent.identity) == agent.dashboard_host_port
    assert agent.browser_gateway_url.startswith("http://127.0.0.1:")


def test_different_agents_usually_get_different_ports() -> None:
    names = ("stm", "alice", "bob", "carol", "dave")
    ports = {
        AgentName.parse(name, "venus.localhost").dashboard_host_port for name in names
    }
    assert len(ports) >= 4
