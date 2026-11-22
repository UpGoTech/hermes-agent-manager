import zlib
from pathlib import Path

from hermes_agent_manager.errors import InstallError

CONTAINER_DASHBOARD_PORT = 9119
HOST_PORT_BASE = 9119
HOST_PORT_SPAN = 100
COMPOSE_PROJECT = "frappe-agents"


def host_dashboard_port(identity: str) -> int:
    digest = zlib.crc32(identity.encode("utf-8")) & 0xFFFFFFFF
    return HOST_PORT_BASE + (digest % HOST_PORT_SPAN)


def ensure_host_port_available(data_root: Path, profile_name: str, port: int) -> None:
    from hermes_agent_manager.agent_paths import list_agent_directories

    for path in list_agent_directories(data_root):
        if path.name == profile_name:
            continue
        marker = path / ".dashboard_port"
        if not marker.is_file():
            continue
        if marker.read_text().strip() != str(port):
            continue
        raise InstallError(
            f"Host dashboard port {port} is already used by agent {path.name}. "
            "Pick a different agent name, or delete the other agent first."
        )
