import sys
from pathlib import Path


def needs_named_volume() -> bool:
    """Docker Desktop virtiofs cannot chmod Unix sockets (gateway.sock → 0600)."""
    if sys.platform == "darwin":
        return True
    return _running_on_wsl()


def _running_on_wsl() -> bool:
    try:
        version = Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False
    return "microsoft" in version or "wsl" in version


def runtime_mount(agent_volume_name: str, host_data_path: Path) -> str:
    if needs_named_volume():
        return agent_volume_name
    return str(host_data_path.resolve())
