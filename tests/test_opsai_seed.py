from pathlib import Path

from hermes_agent_manager.docker_runner import CONTAINER_DATA, DockerRunner
from hermes_agent_manager.opsai_seed import (
    SEED_FILES,
    default_env_values,
    install_opsai_seed,
    seed_root,
)
from tests.fake_commands import FakeCommands


def test_seed_root_contains_required_files() -> None:
    root = seed_root()
    for relative in SEED_FILES:
        assert (root / relative).is_file(), relative
    assert (root / "env.example").is_file()


def test_default_env_values_match_example() -> None:
    values = default_env_values()
    assert values["FRAPPE_URL"]
    assert values["FRAPPE_URL_USER"]
    assert values["FRAPPE_API_KEY"] == "replace-me"
    assert values["FRAPPE_API_SECRET"] == "replace-me"
    assert values["FM_SITE"]


def test_install_opsai_seed_copies_files_and_enables_memory() -> None:
    commands = FakeCommands()
    docker = DockerRunner(commands, available=lambda: True, sleep=lambda _seconds: None)

    install_opsai_seed(docker, "HA-venus-my-agent")

    root = seed_root()
    assert [
        "docker",
        "exec",
        "--user",
        "root",
        "HA-venus-my-agent",
        "mkdir",
        "-p",
        f"{CONTAINER_DATA}/memories",
        f"{CONTAINER_DATA}/skills/erpnext/scripts",
    ] in commands.arguments
    for relative in SEED_FILES:
        assert [
            "docker",
            "cp",
            str(root / relative),
            f"HA-venus-my-agent:{CONTAINER_DATA}/{relative}",
        ] in commands.arguments
    assert [
        "docker",
        "exec",
        "--user",
        "root",
        "HA-venus-my-agent",
        "chmod",
        "+x",
        f"{CONTAINER_DATA}/skills/erpnext/scripts/frappe.py",
    ] in commands.arguments
    assert any(
        item[:2] == ["docker", "exec"]
        and "hermes" in item
        and "config" in item
        and "memory.memory_enabled" in item
        for item in commands.arguments
    )
    assert any(
        item[:2] == ["docker", "exec"]
        and "memory.user_profile_enabled" in item
        for item in commands.arguments
    )
    assert any(
        item[:2] == ["docker", "exec"]
        and any("FRAPPE_API_KEY=" in part for part in item)
        for item in commands.arguments
    )


def test_install_opsai_seed_applies_env_overrides() -> None:
    commands = FakeCommands()
    docker = DockerRunner(commands, available=lambda: True, sleep=lambda _seconds: None)

    install_opsai_seed(
        docker,
        "HA-venus-my-agent",
        {"FRAPPE_URL": "http://venus.localhost", "FM_SITE": "venus.localhost"},
    )

    assert any(
        item[:2] == ["docker", "exec"]
        and any("FRAPPE_URL=http://venus.localhost" in part for part in item)
        and any("FM_SITE=venus.localhost" in part for part in item)
        for item in commands.arguments
    )


def test_ensure_env_skips_when_empty() -> None:
    commands = FakeCommands()
    docker = DockerRunner(commands, available=lambda: True, sleep=lambda _seconds: None)

    docker.ensure_env("HA-venus-my-agent", {})

    assert commands.arguments == []


def test_install_copies_soul_content() -> None:
    soul = Path(seed_root() / "SOUL.md").read_text()
    assert "OpsAi Agent" in soul
    assert "FRAPPE_URL" in soul
