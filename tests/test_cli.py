from typer.testing import CliRunner

from hermes_agent_manager.cli import build_app
from hermes_agent_manager.errors import InstallError


def test_cli_prints_install_errors(monkeypatch) -> None:
    class BrokenInstaller:
        def install(self, _name: str) -> None:
            raise InstallError("nope")

    monkeypatch.setattr("hermes_agent_manager.cli.installer_factory", lambda _progress: BrokenInstaller())
    result = CliRunner().invoke(build_app(), ["create", "my-agent"])

    assert result.exit_code == 1
    assert "nope" in result.output
