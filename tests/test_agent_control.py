from pathlib import Path

import pytest

from hermes_agent_manager.agent_control import AgentControl
from hermes_agent_manager.docker_runner import DockerRunner
from hermes_agent_manager.errors import InstallError
from tests.fake_commands import FakeCommands


def test_lists_agents_with_container_status(tmp_path: Path) -> None:
    data_root = tmp_path / "frappe-agent"
    directory = _mark(data_root)
    commands = FakeCommands()
    commands.existing.add("HA-venus-my-agent")

    records = _control(commands, data_root).list_agents()

    assert records[0].profile_name == "my-agent"
    assert records[0].container_name == "HA-venus-my-agent"
    assert records[0].status == "running"
    assert records[0].image == "ham/hermes-agent:latest"
    assert records[0].fm_site == "venus.localhost"
    assert records[0].fm_network == "fm__venus_localhost__network"
    assert records[0].hermes_alias == "venus-my-agent"
    assert records[0].gateway_url == "http://venus-my-agent:9119"
    assert records[0].data_directory == directory.resolve()


def test_lists_same_agent_name_on_multiple_sites(tmp_path: Path) -> None:
    data_root = tmp_path / "frappe-agent"
    _mark(data_root, site="venus.localhost")
    _mark(data_root, site="fxl.localhost")
    commands = FakeCommands()
    commands.existing.add("HA-venus-my-agent")
    commands.existing.add("HA-fxl-my-agent")

    records = _control(commands, data_root).list_agents()

    assert [(item.profile_name, item.fm_site) for item in records] == [
        ("my-agent", "fxl.localhost"),
        ("my-agent", "venus.localhost"),
    ]


def test_describe_requires_site_when_name_is_ambiguous(tmp_path: Path) -> None:
    data_root = tmp_path / "frappe-agent"
    _mark(data_root, site="venus.localhost")
    _mark(data_root, site="fxl.localhost")

    with pytest.raises(InstallError, match="Pass --site"):
        _control(FakeCommands(), data_root).describe("my-agent")

    record = _control(FakeCommands(), data_root).describe(
        "my-agent", site_name="venus.localhost"
    )
    assert record.container_name == "HA-venus-my-agent"
    assert record.fm_site == "venus.localhost"


def test_describes_a_missing_container(tmp_path: Path) -> None:
    commands = FakeCommands()
    commands.status = "absent"

    record = _control(commands, tmp_path).describe("my-agent")

    assert record.status == "absent"
    assert record.image == ""


def test_starts_stops_and_restarts_the_container(tmp_path: Path) -> None:
    data_root = tmp_path / "frappe-agent"
    _mark(data_root)
    commands = FakeCommands()
    commands.existing.add("HA-venus-my-agent")
    control = _control(commands, data_root)

    control.start("my-agent")
    control.stop("my-agent")
    control.restart("my-agent")

    assert ["docker", "start", "HA-venus-my-agent"] in commands.arguments
    assert ["docker", "stop", "HA-venus-my-agent"] in commands.arguments
    assert ["docker", "restart", "HA-venus-my-agent"] in commands.arguments


def test_shell_runs_inside_the_container(tmp_path: Path) -> None:
    data_root = tmp_path / "frappe-agent"
    _mark(data_root)
    commands = FakeCommands()
    commands.existing.add("HA-venus-my-agent")
    attached: list[list[str]] = []
    control = _control(commands, data_root, attached)

    control.shell("my-agent")

    assert attached == [[
        "docker", "exec", "-it", "--user", "hermes",
        "--workdir", "/opt/data", "-e", "HERMES_HOME=/opt/data",
        "HA-venus-my-agent", "bash",
    ]]


def test_delete_removes_container_volume_and_data_directory(tmp_path: Path) -> None:
    data_root = tmp_path / "frappe-agent"
    directory = _mark(data_root, volume="ham-venus-my-agent")
    site_directory = directory.parent
    commands = FakeCommands()
    commands.existing.add("HA-venus-my-agent")
    commands.volumes.add("ham-venus-my-agent")

    _control(commands, data_root).delete("my-agent")

    assert ["docker", "rm", "-f", "HA-venus-my-agent"] in commands.arguments
    assert ["docker", "volume", "rm", "ham-venus-my-agent"] in commands.arguments
    assert not directory.exists()
    assert not site_directory.exists()


def test_delete_rejects_an_unknown_agent(tmp_path: Path) -> None:
    with pytest.raises(InstallError, match="does not exist"):
        _control(FakeCommands(), tmp_path).delete("my-agent")


def test_backup_archives_host_directory(tmp_path: Path) -> None:
    data_root = tmp_path / "frappe-agent"
    directory = _mark(data_root)
    (directory / "note.txt").write_text("hello")
    commands = FakeCommands()
    commands.status = "running"

    archive = _control(commands, data_root).backup("my-agent", tmp_path / "out.tar.gz")

    assert archive.name == "out.tar.gz"
    assert archive.is_file()
    assert ["docker", "stop", "HA-venus-my-agent"] in commands.arguments
    assert ["docker", "start", "HA-venus-my-agent"] in commands.arguments


def test_restore_imports_into_host_directory(tmp_path: Path) -> None:
    data_root = tmp_path / "frappe-agent"
    directory = _mark(data_root)
    source = tmp_path / "staging" / "my-agent"
    source.mkdir(parents=True)
    (source / "note.txt").write_text("hello")
    (source / ".site").write_text("venus.localhost\n")
    import tarfile

    archive = tmp_path / "my-agent.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(source, arcname="my-agent")
    commands = FakeCommands()
    commands.status = "exited"

    _control(commands, data_root).restore("my-agent", archive)

    assert (directory / "note.txt").read_text() == "hello"
    assert (directory / ".site").read_text() == "venus.localhost\n"


def _mark(
    data_root: Path,
    volume: str | None = None,
    site: str = "venus.localhost",
) -> Path:
    directory = data_root / site / "my-agent"
    directory.mkdir(parents=True)
    (directory / ".site").write_text(f"{site}\n")
    slug = site.removesuffix(".localhost").replace(".", "-")
    (directory / ".gateway_url").write_text(f"http://{slug}-my-agent:9119\n")
    if volume:
        (directory / ".volume").write_text(f"{volume}\n")
    return directory


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
