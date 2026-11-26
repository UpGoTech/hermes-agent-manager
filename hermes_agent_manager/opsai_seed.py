from pathlib import Path

from hermes_agent_manager.docker_runner import CONTAINER_DATA, DockerRunner

SEED_FILES = (
    "SOUL.md",
    "memories/MEMORY.md",
    "memories/USER.md",
    "skills/erpnext/SKILL.md",
    "skills/erpnext/scripts/frappe.py",
)

_MEMORY_SETTINGS = (
    ("memory.memory_enabled", "true"),
    ("memory.user_profile_enabled", "true"),
)


def seed_root() -> Path:
    return Path(__file__).resolve().parent / "seed"


def default_env_values() -> dict[str, str]:
    return _parse_env_file(seed_root() / "env.example")


def install_opsai_seed(
    docker: DockerRunner,
    container_name: str,
    env: dict[str, str] | None = None,
) -> None:
    root = seed_root()
    docker.exec_as_root(
        container_name,
        [
            "mkdir",
            "-p",
            f"{CONTAINER_DATA}/memories",
            f"{CONTAINER_DATA}/skills/erpnext/scripts",
        ],
    )
    for relative in SEED_FILES:
        docker.copy_to_container(
            container_name,
            str(root / relative),
            f"{CONTAINER_DATA}/{relative}",
        )
    docker.exec_as_root(
        container_name,
        ["chmod", "+x", f"{CONTAINER_DATA}/skills/erpnext/scripts/frappe.py"],
    )
    for key, value in _MEMORY_SETTINGS:
        docker.exec_as_hermes(
            container_name,
            ["hermes", "config", "set", key, value],
        )
    docker.ensure_env(container_name, {**default_env_values(), **(env or {})})


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values
