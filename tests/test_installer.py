from pathlib import Path

import pytest

from hermes_agent_manager.docker_runner import IMAGE, DockerRunner
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.installer import AgentInstaller
from hermes_agent_manager.progress import Progress
from tests.fake_commands import FakeCommands


def test_install_runs_expected_docker_commands(tmp_path: Path) -> None:
    commands = FakeCommands()
    installer = _installer(commands, tmp_path)

    installer.install("my-agent")

    data = tmp_path / "my-agent"
    assert commands.arguments == [
        ["docker", "container", "inspect", "HA-my-agent"],
        ["docker", "pull", IMAGE],
        [
            "docker",
            "run",
            "-d",
            "--name",
            "HA-my-agent",
            "--restart",
            "unless-stopped",
            "-v",
            f"{data}:/opt/data",
            "-e",
            "HERMES_UID=1000",
            "-e",
            "HERMES_GID=1000",
            "-e",
            "HERMES_HOME=/opt/data",
            IMAGE,
            "gateway",
            "run",
        ],
        ["docker", "inspect", "--format", "{{.State.Status}}", "HA-my-agent"],
        [
            "docker",
            "exec",
            "--workdir",
            "/opt/data",
            "-e",
            "HERMES_HOME=/opt/data",
            "HA-my-agent",
            "hermes",
            "profile",
            "create",
            "my-agent",
        ],
    ]
    assert data.is_dir()


def test_rejects_an_existing_container(tmp_path: Path) -> None:
    commands = FakeCommands()
    commands.existing.add("HA-my-agent")

    with pytest.raises(InstallError, match="HA-my-agent already exists"):
        _installer(commands, tmp_path).install("my-agent")

    assert commands.arguments == [["docker", "container", "inspect", "HA-my-agent"]]


def test_rejects_an_existing_data_directory(tmp_path: Path) -> None:
    (tmp_path / "my-agent").mkdir()
    commands = FakeCommands()

    with pytest.raises(InstallError, match="already exists"):
        _installer(commands, tmp_path).install("my-agent")

    assert "pull" not in [item[1] for item in commands.arguments]


def test_rejects_missing_docker(tmp_path: Path) -> None:
    commands = FakeCommands()
    installer = _installer(commands, tmp_path, available=lambda: False)

    with pytest.raises(InstallError, match="Docker is not available"):
        installer.install("my-agent")

    assert commands.arguments == []


def test_reports_docker_stderr(tmp_path: Path) -> None:
    commands = FakeCommands()
    commands.failures["pull"] = "pull denied"

    with pytest.raises(InstallError, match="pull denied"):
        _installer(commands, tmp_path).install("my-agent")


def test_reports_each_install_step(tmp_path: Path) -> None:
    progress = RecordingProgress()
    installer = _installer(FakeCommands(), tmp_path, progress=progress)

    installer.install("my-agent")

    data = tmp_path / "my-agent"
    assert progress.messages == [
        f"Pulling {IMAGE}",
        f"Creating {data}",
        "Starting container HA-my-agent",
        "Waiting for HA-my-agent",
        "Creating profile my-agent in HA-my-agent at /opt/data",
    ]


def test_reports_a_container_that_does_not_start(tmp_path: Path) -> None:
    commands = FakeCommands()
    commands.status = "created"
    installer = _installer(commands, tmp_path, attempts=2)

    with pytest.raises(InstallError, match="did not start"):
        installer.install("my-agent")


class RecordingProgress(Progress):
    def __init__(self) -> None:
        self.messages: list[str] = []

    def run(self, message: str, action):
        self.messages.append(message)
        return action()


def _installer(
    commands: FakeCommands,
    data_root: Path,
    available=lambda: True,
    attempts: int = 1,
    progress: Progress | None = None,
) -> AgentInstaller:
    docker = DockerRunner(
        commands,
        available=available,
        sleep=lambda _seconds: None,
        attempts=attempts,
    )
    return AgentInstaller(docker, data_root, user_id=1000, group_id=1000, progress=progress)
