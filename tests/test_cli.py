from pathlib import Path

from rich.console import Console
from typer.testing import CliRunner

from hermes_agent_manager.agent_control import AgentRecord
from hermes_agent_manager.agent_name import AgentName
from hermes_agent_manager.cli import build_app
from hermes_agent_manager.display import (
    detail_status,
    info_rows,
    list_status,
    print_agent_list,
    print_create_summary,
)
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.installer import InstallResult


def test_cli_prints_install_errors(monkeypatch) -> None:
    class BrokenInstaller:
        def install(self, _name: str, *_args, **_kwargs) -> None:
            raise InstallError("nope")

    monkeypatch.setattr("hermes_agent_manager.cli.installer_factory", lambda _progress: BrokenInstaller())
    result = CliRunner().invoke(
        build_app(),
        ["create", "my-agent", "--site", "venus.localhost", "--user", "alice"],
    )

    assert result.exit_code == 1
    assert "nope" in result.output


def test_cli_seed_reports_success(monkeypatch) -> None:
    agent = AgentName.parse("stm", "venus.localhost")
    seen: dict[str, str | None] = {}

    class FakeControl:
        def seed(
            self,
            _name: str,
            _site: str | None = None,
            seed_ref: str | None = None,
        ):
            seen["seed_ref"] = seed_ref
            return agent

    monkeypatch.setattr(
        "hermes_agent_manager.cli.controller_factory",
        lambda _progress: FakeControl(),
    )
    result = CliRunner().invoke(
        build_app(),
        ["seed", "stm", "--site", "venus.localhost", "--seed-ref", "opsai-seed-v1.0.0"],
    )

    assert result.exit_code == 0
    assert "Seeded OpsAi files in HA-venus-stm" in result.output
    assert seen["seed_ref"] == "opsai-seed-v1.0.0"


def test_cli_prints_create_summary(monkeypatch) -> None:
    agent = AgentName.parse("stm", "venus.localhost")

    class FakeInstaller:
        def install(self, _name: str, *_args, **_kwargs):
            return InstallResult(agent, "alice", "secret", Path("/tmp/stm"))

    monkeypatch.setattr(
        "hermes_agent_manager.cli.installer_factory",
        lambda _progress: FakeInstaller(),
    )
    result = CliRunner().invoke(
        build_app(),
        ["create", "stm", "--site", "venus.localhost", "--user", "alice"],
    )

    assert result.exit_code == 0
    assert "Created agent" in result.output
    assert "HA-venus-stm" in result.output
    assert "http://venus-stm:9119" in result.output
    assert "alice" in result.output
    assert "secret" in result.output
    assert "OpsAi Settings" in result.output


def test_info_rows_match_frappe_manager_shape() -> None:
    record = _record("running")
    rows = dict(info_rows(record))

    assert rows["Agent"] == "stm"
    assert rows["Container"] == "HA-venus-stm"
    assert rows["Status"] == "[green]Active[/green]"
    assert rows["Compose Group"] == "frappe-agents"
    assert rows["OpsAi Gateway"] == "http://venus-stm:9119"
    assert rows["Dashboard User"] == "alice"
    assert rows["Password"] == "secret"
    assert rows["Data"] == "/tmp/stm"
    assert "Browser Gateway" not in rows
    assert "Volume" not in rows
    assert detail_status("exited") == "[red]Exited[/red]"


def test_list_status_matches_fm_active_inactive() -> None:
    assert list_status("running") == "[green]Active[/green]"
    assert list_status("exited") == "[red]Inactive[/red]"
    assert list_status("absent") == "[red]Absent[/red]"


def test_list_table_includes_gateway_and_path() -> None:
    console = Console(record=True, width=120)
    print_agent_list([_record("running")], console)
    text = console.export_text()

    assert "Agent" in text
    assert "Status" in text
    assert "FM Site" in text
    assert "OpsAi Gateway" in text
    assert "stm" in text
    assert "Active" in text
    assert "http://venus-stm:9119" in text


def test_create_summary_table(tmp_path: Path) -> None:
    console = Console(record=True, width=120)
    print_create_summary(
        AgentName.parse("stm", "venus.localhost"),
        "alice",
        "secret",
        tmp_path / "stm",
        console,
    )
    text = console.export_text()

    assert "Created agent stm" in text
    assert "Username" in text
    assert "Password" in text
    assert "secret" in text
    assert "http://127.0.0.1:" in text
    assert "OpsAi Settings" in text


def _record(status: str) -> AgentRecord:
    return AgentRecord(
        profile_name="stm",
        container_name="HA-venus-stm",
        status=status,
        data_directory=Path("/tmp/stm"),
        image="ham/hermes-agent:latest",
        fm_site="venus.localhost",
        fm_network="fm__venus_localhost__network",
        hermes_alias="venus-stm",
        gateway_url="http://venus-stm:9119",
        browser_gateway_url="http://127.0.0.1:9150",
        dashboard_user="alice",
        dashboard_password="secret",
        dashboard_port="9150",
    )
