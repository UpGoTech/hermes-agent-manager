from pathlib import Path

import pytest

from hermes_agent_manager.docker_runner import IMAGE, DockerRunner
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.image import build_context
from hermes_agent_manager.installer import AgentInstaller
from hermes_agent_manager.progress import Progress
from tests.fake_commands import FakeCommands


def test_install_builds_missing_image_then_runs_gateway(tmp_path: Path) -> None:
    commands = FakeCommands()
    installer = _installer(commands, tmp_path)

    installer.install("my-agent")

    marker = tmp_path / "my-agent"
    context = str(build_context())
    assert commands.arguments == [
        ["docker", "container", "inspect", "HA-my-agent"],
        ["docker", "volume", "inspect", "ham-my-agent"],
        ["docker", "image", "inspect", IMAGE],
        ["docker", "build", "-t", IMAGE, context],
        ["docker", "volume", "inspect", "ham-my-agent"],
        ["docker", "volume", "create", "ham-my-agent"],
        [
            "docker",
            "run",
            "-d",
            "--name",
            "HA-my-agent",
            "--hostname",
            "my-agent.localhost",
            "--restart",
            "unless-stopped",
            "-v",
            "ham-my-agent:/opt/data",
            "-e",
            "HERMES_UID=1000",
            "-e",
            "HERMES_GID=1000",
            "-e",
            "HERMES_HOME=/opt/data",
            "-e",
            "HAM_AGENT=my-agent",
            IMAGE,
            "gateway",
            "run",
        ],
        ["docker", "inspect", "--format", "{{.State.Status}}", "HA-my-agent"],
        [
            "docker",
            "exec",
            "--user",
            "hermes",
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
    assert marker.is_dir()
    assert (marker / ".volume").read_text() == "ham-my-agent\n"


def test_install_skips_build_when_image_exists(tmp_path: Path) -> None:
    commands = FakeCommands()
    commands.images.add(IMAGE)
    installer = _installer(commands, tmp_path)

    installer.install("my-agent")

    assert ["docker", "build", "-t", IMAGE, str(build_context())] not in commands.arguments
    assert ["docker", "image", "inspect", IMAGE] in commands.arguments


def test_rejects_an_existing_container(tmp_path: Path) -> None:
    commands = FakeCommands()
    commands.existing.add("HA-my-agent")

    with pytest.raises(InstallError, match="HA-my-agent already exists"):
        _installer(commands, tmp_path).install("my-agent")

    assert commands.arguments == [["docker", "container", "inspect", "HA-my-agent"]]


def test_rejects_an_existing_volume(tmp_path: Path) -> None:
    commands = FakeCommands()
    commands.volumes.add("ham-my-agent")

    with pytest.raises(InstallError, match="ham-my-agent already exists"):
        _installer(commands, tmp_path).install("my-agent")


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
    commands.failures["build"] = "build failed"

    with pytest.raises(InstallError, match="build failed"):
        _installer(commands, tmp_path).install("my-agent")


def test_reports_each_install_step(tmp_path: Path) -> None:
    progress = RecordingProgress()
    installer = _installer(FakeCommands(), tmp_path, progress=progress)

    installer.install("my-agent")

    marker = tmp_path / "my-agent"
    assert progress.messages == [
        f"Ensuring image {IMAGE}",
        "Creating volume ham-my-agent",
        f"Creating {marker}",
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


def test_build_image_pulls_base_and_tags_ham_image() -> None:
    commands = FakeCommands()
    docker = DockerRunner(commands, available=lambda: True, sleep=lambda _seconds: None)

    docker.build_image(IMAGE, pull=True)

    assert commands.arguments == [
        ["docker", "build", "-t", IMAGE, "--pull", str(build_context())],
    ]


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
