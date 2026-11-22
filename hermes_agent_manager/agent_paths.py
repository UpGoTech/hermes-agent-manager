from pathlib import Path

from hermes_agent_manager.fm_site import frappe_manager_home


def frappe_agent_root(fm_home: Path | None = None) -> Path:
    return (fm_home or frappe_manager_home()).expanduser().resolve() / "frappe-agent"


def agent_data_directory(data_root: Path, site_name: str, profile_name: str) -> Path:
    return (data_root / site_name / profile_name).resolve()


def list_agent_directories(data_root: Path) -> list[Path]:
    if not data_root.is_dir():
        return []
    found: list[Path] = []
    for site_directory in sorted(data_root.iterdir()):
        if not site_directory.is_dir():
            continue
        for agent_directory in sorted(site_directory.iterdir()):
            if agent_directory.is_dir() and (agent_directory / ".site").is_file():
                found.append(agent_directory)
    return found


def find_agent_directories(data_root: Path, profile_name: str) -> list[Path]:
    return [
        path
        for path in list_agent_directories(data_root)
        if path.name == profile_name
    ]
