from pathlib import Path

import pytest

from hermes_agent_manager.docker_runner import IMAGE, DockerRunner
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.image import build_context
from hermes_agent_manager.installer import AgentInstaller
from hermes_agent_manager.progress import Progress
from tests.fake_commands import FakeCommands


def test_install_builds_missing_image_then_runs_gateway(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "hermes_agent_manager.installer.new_dashboard_password",
        lambda: "dash-pass",
    )
    monkeypatch.setattr("hermes_agent_manager.installer.needs_named_volume", lambda: True)
    commands = FakeCommands()
    fm_home = _fm_home(tmp_path, commands)
    data_root = tmp_path / "frappe-agent"
    installer = _installer(commands, data_root, fm_home=fm_home)

    installer.install("my-agent", "venus.localhost", "alice")

    marker = data_root / "venus.localhost" / "my-agent"
    context = str(build_context())
    port = 9119 + (__import__("zlib").crc32(b"venus-my-agent") & 0xFFFFFFFF) % 100
    assert ["docker", "image", "inspect", IMAGE] in commands.arguments
    assert ["docker", "build", "-t", IMAGE, context] in commands.arguments
    assert ["docker", "volume", "create", "ham-venus-my-agent"] in commands.arguments
    assert any(
        item[:3] == ["docker", "run", "-d"]
        and "ham-venus-my-agent:/opt/data" in item
        and "HAM_AGENT=my-agent" in item
        and "venus.localhost:host-gateway" in item
        and "FRAPPE_URL=http://venus.localhost" in item
        and "HERMES_DASHBOARD=1" in item
        and f"127.0.0.1:{port}:9119" in item
        and "HERMES_DASHBOARD_BASIC_AUTH_USERNAME=alice" in item
        and "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=dash-pass" in item
        and "HERMES_GATEWAY_URL=http://venus-my-agent:9119" in item
        and "com.docker.compose.project=frappe-agents" in item
        for item in commands.arguments
    )
    assert [
        "docker",
        "network",
        "connect",
        "--alias",
        "venus-my-agent",
        "fm__venus_localhost__network",
        "HA-venus-my-agent",
    ] in commands.arguments
    assert marker.is_dir()
    assert (marker / ".site").read_text() == "venus.localhost\n"
    assert (marker / ".gateway_url").read_text() == "http://venus-my-agent:9119\n"
    assert (marker / ".dashboard_user").read_text() == "alice\n"
    assert (marker / ".dashboard_password").read_text() == "dash-pass\n"
    assert (marker / ".dashboard_port").read_text() == f"{port}\n"
    assert (marker / ".volume").read_text() == "ham-venus-my-agent\n"


def test_install_bind_mounts_on_linux(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "hermes_agent_manager.installer.new_dashboard_password",
        lambda: "dash-pass",
    )
    monkeypatch.setattr("hermes_agent_manager.installer.needs_named_volume", lambda: False)
    commands = FakeCommands()
    fm_home = _fm_home(tmp_path, commands)
    data_root = tmp_path / "frappe-agent"
    installer = _installer(commands, data_root, fm_home=fm_home)

    installer.install("my-agent", "venus.localhost", "alice")

    marker = data_root / "venus.localhost" / "my-agent"
    host_path = str(marker.resolve())
    assert ["docker", "volume", "create", "ham-venus-my-agent"] not in commands.arguments
    assert any(
        item[:3] == ["docker", "run", "-d"] and f"{host_path}:/opt/data" in item
        for item in commands.arguments
    )
    assert not (marker / ".volume").exists()


def test_install_skips_build_when_image_exists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "hermes_agent_manager.installer.new_dashboard_password",
        lambda: "dash-pass",
    )
    monkeypatch.setattr("hermes_agent_manager.installer.needs_named_volume", lambda: True)
    commands = FakeCommands()
    commands.images.add(IMAGE)
    fm_home = _fm_home(tmp_path, commands)
    data_root = tmp_path / "frappe-agent"
    installer = _installer(commands, data_root, fm_home=fm_home)

    installer.install("my-agent", "venus.localhost", "alice")

    assert ["docker", "build", "-t", IMAGE, str(build_context())] not in commands.arguments


def test_rejects_dashboard_port_collision(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hermes_agent_manager.installer.needs_named_volume", lambda: True)
    port = 9119 + (__import__("zlib").crc32(b"venus-my-agent") & 0xFFFFFFFF) % 100
    data_root = tmp_path / "frappe-agent"
    other = data_root / "venus.localhost" / "other-agent"
    other.mkdir(parents=True)
    (other / ".site").write_text("venus.localhost\n")
    (other / ".dashboard_port").write_text(f"{port}\n")
    commands = FakeCommands()
    fm_home = _fm_home(tmp_path, commands)

    with pytest.raises(InstallError, match="already used by agent other-agent"):
        _installer(commands, data_root, fm_home=fm_home).install(
            "my-agent", "venus.localhost", "alice"
        )


def test_rejects_missing_fm_sites(tmp_path: Path) -> None:
    (tmp_path / "fm" / "sites").mkdir(parents=True)
    commands = FakeCommands()
    with pytest.raises(InstallError, match="No Frappe Manager sites"):
        _installer(commands, tmp_path / "frappe-agent", fm_home=tmp_path / "fm").install(
            "my-agent", "x", "alice"
        )


def test_rejects_an_existing_container(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hermes_agent_manager.installer.needs_named_volume", lambda: True)
    commands = FakeCommands()
    fm_home = _fm_home(tmp_path, commands)
    commands.existing.add("HA-venus-my-agent")

    with pytest.raises(InstallError, match="HA-venus-my-agent already exists"):
        _installer(commands, tmp_path / "frappe-agent", fm_home=fm_home).install(
            "my-agent", "venus.localhost", "alice"
        )


def test_rejects_an_existing_data_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hermes_agent_manager.installer.needs_named_volume", lambda: True)
    data_root = tmp_path / "frappe-agent"
    (data_root / "venus.localhost" / "my-agent").mkdir(parents=True)
    commands = FakeCommands()
    fm_home = _fm_home(tmp_path, commands)

    with pytest.raises(InstallError, match="already exists"):
        _installer(commands, data_root, fm_home=fm_home).install(
            "my-agent", "venus.localhost", "alice"
        )


def test_rejects_missing_docker(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("hermes_agent_manager.installer.needs_named_volume", lambda: True)
    commands = FakeCommands()
    fm_home = _fm_home(tmp_path, commands)
    installer = _installer(
        commands,
        tmp_path / "frappe-agent",
        available=lambda: False,
        fm_home=fm_home,
    )

    with pytest.raises(InstallError, match="Docker is not available"):
        installer.install("my-agent", "venus.localhost", "alice")

    assert commands.arguments == []


def test_reports_docker_stderr(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "hermes_agent_manager.installer.new_dashboard_password",
        lambda: "dash-pass",
    )
    monkeypatch.setattr("hermes_agent_manager.installer.needs_named_volume", lambda: True)
    commands = FakeCommands()
    fm_home = _fm_home(tmp_path, commands)
    commands.failures["build"] = "build failed"

    with pytest.raises(InstallError, match="build failed"):
        _installer(commands, tmp_path / "frappe-agent", fm_home=fm_home).install(
            "my-agent", "venus.localhost", "alice"
        )


def test_reports_each_install_step(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "hermes_agent_manager.installer.new_dashboard_password",
        lambda: "dash-pass",
    )
    monkeypatch.setattr("hermes_agent_manager.installer.needs_named_volume", lambda: True)
    progress = RecordingProgress()
    commands = FakeCommands()
    fm_home = _fm_home(tmp_path, commands)
    data_root = tmp_path / "frappe-agent"
    installer = _installer(commands, data_root, progress=progress, fm_home=fm_home)

    result = installer.install("my-agent", "venus.localhost", "alice")

    marker = data_root / "venus.localhost" / "my-agent"
    assert progress.messages == [
        f"Ensuring image {IMAGE}",
        "Creating volume ham-venus-my-agent",
        f"Creating {marker.resolve()}",
        "Starting container HA-venus-my-agent",
        "Waiting for HA-venus-my-agent",
        "Creating profile my-agent in HA-venus-my-agent at /opt/data",
        "Joining network fm__venus_localhost__network",
        "Recording FM site venus.localhost",
    ]
    assert progress.notes == []
    assert result.dashboard_user == "alice"
    assert result.dashboard_password == "dash-pass"
    assert result.agent.container_name == "HA-venus-my-agent"
    assert result.data_directory == marker.resolve()


def test_reports_a_container_that_does_not_start(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "hermes_agent_manager.installer.new_dashboard_password",
        lambda: "dash-pass",
    )
    monkeypatch.setattr("hermes_agent_manager.installer.needs_named_volume", lambda: True)
    commands = FakeCommands()
    fm_home = _fm_home(tmp_path, commands)
    commands.statuses["HA-venus-my-agent"] = "created"
    installer = _installer(
        commands,
        tmp_path / "frappe-agent",
        attempts=2,
        fm_home=fm_home,
    )

    with pytest.raises(InstallError, match="did not start"):
        installer.install("my-agent", "venus.localhost", "alice")


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
        self.notes: list[str] = []

    def run(self, message: str, action):
        self.messages.append(message)
        return action()

    def done(self, message: str) -> None:
        self.notes.append(message)


def _fm_home(tmp_path: Path, commands: FakeCommands) -> Path:
    home = tmp_path / "fm"
    site = home / "sites" / "venus.localhost"
    site.mkdir(parents=True)
    (site / "docker-compose.yml").write_text("services: {}\n")
    commands.networks.add("fm__venus_localhost__network")
    commands.existing.add("fm__venus_localhost__frappe")
    return home


def _installer(
    commands: FakeCommands,
    data_root: Path,
    available=lambda: True,
    attempts: int = 1,
    progress: Progress | None = None,
    fm_home: Path | None = None,
) -> AgentInstaller:
    docker = DockerRunner(
        commands,
        available=available,
        sleep=lambda _seconds: None,
        attempts=attempts,
    )
    return AgentInstaller(
        docker,
        data_root,
        user_id=1000,
        group_id=1000,
        progress=progress,
        fm_home=fm_home,
        interactive=False,
    )
