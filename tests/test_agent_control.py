from pathlib import Path

import pytest

from hermes_agent_manager.agent_control import AgentControl
from hermes_agent_manager.docker_runner import DockerRunner
from hermes_agent_manager.errors import InstallError
from tests.fake_commands import FakeCommands


def test_lists_agents_with_container_status(tmp_path: Path) -> None:
    (tmp_path / "my-agent").mkdir()
    commands = FakeCommands()
    commands.existing.add("HA-my-agent")

    records = _control(commands, tmp_path).list_agents()

    assert records[0].profile_name == "my-agent"
    assert records[0].container_name == "HA-my-agent"
    assert records[0].status == "running"
    assert records[0].image == "ham/hermes-agent:latest"


def test_describes_a_missing_container(tmp_path: Path) -> None:
    commands = FakeCommands()
    commands.status = "absent"

    record = _control(commands, tmp_path).describe("my-agent")

    assert record.status == "absent"
    assert record.image == ""


def test_starts_stops_and_restarts_the_container(tmp_path: Path) -> None:
    commands = FakeCommands()
    commands.existing.add("HA-my-agent")
    control = _control(commands, tmp_path)

    control.start("my-agent")
    control.stop("my-agent")
    control.restart("my-agent")

    assert ["docker", "start", "HA-my-agent"] in commands.arguments
    assert ["docker", "stop", "HA-my-agent"] in commands.arguments
    assert ["docker", "restart", "HA-my-agent"] in commands.arguments


def test_shell_runs_inside_the_container(tmp_path: Path) -> None:
    commands = FakeCommands()
    commands.existing.add("HA-my-agent")
    attached: list[list[str]] = []
    control = _control(commands, tmp_path, attached)

    control.shell("my-agent")

    assert attached == [[
        "docker", "exec", "-it", "--user", "hermes",
        "--workdir", "/opt/data", "-e", "HERMES_HOME=/opt/data",
        "HA-my-agent", "bash",
    ]]


def test_delete_removes_container_volume_and_marker(tmp_path: Path) -> None:
    directory = tmp_path / "my-agent"
    directory.mkdir()
    commands = FakeCommands()
    commands.existing.add("HA-my-agent")
    commands.volumes.add("ham-my-agent")

    _control(commands, tmp_path).delete("my-agent")

    assert ["docker", "rm", "-f", "HA-my-agent"] in commands.arguments
    assert ["docker", "volume", "rm", "ham-my-agent"] in commands.arguments
    assert not directory.exists()


def test_delete_rejects_an_unknown_agent(tmp_path: Path) -> None:
    with pytest.raises(InstallError, match="does not exist"):
        _control(FakeCommands(), tmp_path).delete("my-agent")


def test_backup_exports_volume_and_restarts_running_container(tmp_path: Path) -> None:
    (tmp_path / "my-agent").mkdir()
    commands = FakeCommands()
    commands.status = "running"
    commands.volumes.add("ham-my-agent")

    archive = _control(commands, tmp_path).backup("my-agent", None)

    assert archive.name == "my-agent.tar.gz"
    assert ["docker", "stop", "HA-my-agent"] in commands.arguments
    assert ["docker", "start", "HA-my-agent"] in commands.arguments
    assert any(item[:2] == ["docker", "run"] and "ham-my-agent:/from:ro" in item for item in commands.arguments)


def test_restore_imports_volume(tmp_path: Path) -> None:
    archive = tmp_path / "my-agent.tar.gz"
    source = tmp_path / "source" / "my-agent"
    source.mkdir(parents=True)
    (source / "note.txt").write_text("hello")
    import tarfile

    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(source, arcname="my-agent")
    commands = FakeCommands()
    commands.status = "exited"

    _control(commands, tmp_path).restore("my-agent", archive)

    assert any(item[:2] == ["docker", "run"] and "ham-my-agent:/to" in item for item in commands.arguments)
    assert (tmp_path / "my-agent" / ".volume").read_text() == "ham-my-agent\n"


def _control(
    commands: FakeCommands,
    data_root: Path,
    attached: list[list[str]] | None = None,
) -> AgentControl:
    docker = DockerRunner(
        commands,
        available=lambda: True,
        attached=_record(attached),
    )
    return AgentControl(docker, data_root)


def _record(attached: list[list[str]] | None):
    def run(arguments: list[str]) -> int:
        if attached is not None:
            attached.append(arguments)
        return 0

    return run
