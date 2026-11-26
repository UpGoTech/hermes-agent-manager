from pathlib import Path

from hermes_agent_manager.docker_runner import CONTAINER_DATA, DockerRunner
from hermes_agent_manager.opsai_seed import (
    SEED_FILES,
    default_env_values,
    install_opsai_seed,
)
from tests.conftest import REPO_SEED
from tests.fake_commands import FakeCommands


def test_repo_seed_contains_required_files() -> None:
    for relative in SEED_FILES:
        assert (REPO_SEED / relative).is_file(), relative


def test_default_env_values_are_static() -> None:
    values = default_env_values()
    assert values["FRAPPE_URL"]
    assert values["FRAPPE_URL_USER"]
    assert values["FRAPPE_API_KEY"] == "replace-me"
    assert values["FRAPPE_API_SECRET"] == "replace-me"
    assert values["FM_SITE"]


def test_install_opsai_seed_copies_soul_and_skills() -> None:
    commands = FakeCommands()
    docker = DockerRunner(commands, available=lambda: True, sleep=lambda _seconds: None)

    install_opsai_seed(docker, "HA-venus-my-agent", seed_root=REPO_SEED)

    assert [
        "docker",
        "exec",
        "--user",
        "root",
        "HA-venus-my-agent",
        "mkdir",
        "-p",
        f"{CONTAINER_DATA}/skills/erpnext/scripts",
    ] in commands.arguments
    for relative in SEED_FILES:
        assert [
            "docker",
            "cp",
            str(REPO_SEED / relative),
            f"HA-venus-my-agent:{CONTAINER_DATA}/{relative}",
        ] in commands.arguments
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
        seed_root=REPO_SEED,
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


def test_repo_seed_soul_content() -> None:
    soul = Path(REPO_SEED / "SOUL.md").read_text()
    assert "OpsAi Agent" in soul
    assert "FRAPPE_URL" in soul
