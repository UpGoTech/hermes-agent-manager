from pathlib import Path

from hermes_agent_manager.agent_paths import (
    agent_data_directory,
    find_agent_directories,
    frappe_agent_root,
    list_agent_directories,
)


def test_frappe_agent_root_under_fm_home(tmp_path: Path) -> None:
    assert frappe_agent_root(tmp_path) == (tmp_path / "frappe-agent").resolve()


def test_agent_data_directory_nests_site_and_agent(tmp_path: Path) -> None:
    root = tmp_path / "frappe-agent"
    path = agent_data_directory(root, "venus.localhost", "purchase")
    assert path == (root / "venus.localhost" / "purchase").resolve()


def test_lists_and_finds_agent_directories(tmp_path: Path) -> None:
    root = tmp_path / "frappe-agent"
    first = root / "venus.localhost" / "purchase"
    second = root / "fxl.localhost" / "store"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / ".site").write_text("venus.localhost\n")
    (second / ".site").write_text("fxl.localhost\n")
    (root / "venus.localhost" / "orphan").mkdir()

    listed = list_agent_directories(root)

    assert listed == [second.resolve(), first.resolve()]
    assert find_agent_directories(root, "purchase") == [first.resolve()]
