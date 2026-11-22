import os
from pathlib import Path
from typing import NoReturn

import typer
from rich.console import Console
from rich.table import Table

from hermes_agent_manager.agent_control import AgentControl, AgentRecord
from hermes_agent_manager.docker_runner import DockerRunner
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.installer import AgentInstaller
from hermes_agent_manager.progress import ConsoleProgress, Progress

app = typer.Typer(add_completion=False, no_args_is_help=True)


def installer_factory(progress: Progress) -> AgentInstaller:
    return AgentInstaller(
        DockerRunner(),
        _data_root(),
        os.getuid(),
        os.getgid(),
        progress,
    )


def controller_factory(progress: Progress) -> AgentControl:
    return AgentControl(DockerRunner(), _data_root(), progress)


@app.command()
def create(agent_name: str = typer.Argument(help="Hermes profile name")) -> None:
    """Install an agent container and profile."""
    progress = ConsoleProgress()
    try:
        agent = installer_factory(progress).install(agent_name)
    except InstallError as error:
        _fail(progress, error)
    progress.done(
        f"Installed profile {agent.profile_name} in container {agent.container_name} "
        "at /opt/data. The container gateway serves this profile."
    )


@app.command("list")
def list_agents() -> None:
    """List agents."""
    records = _call(lambda progress: controller_factory(progress).list_agents())
    _print_table(records)


@app.command()
def info(agent_name: str = typer.Argument(help="Hermes profile name")) -> None:
    """Show one agent."""
    record = _call(lambda progress: controller_factory(progress).describe(agent_name))
    _print_info(record)


@app.command()
def start(agent_name: str = typer.Argument(help="Hermes profile name")) -> None:
    """Start an agent container."""
    agent = _call(lambda progress: controller_factory(progress).start(agent_name))
    ConsoleProgress().done(f"Started {agent.container_name}.")


@app.command()
def stop(agent_name: str = typer.Argument(help="Hermes profile name")) -> None:
    """Stop an agent container."""
    agent = _call(lambda progress: controller_factory(progress).stop(agent_name))
    ConsoleProgress().done(f"Stopped {agent.container_name}.")


@app.command()
def restart(agent_name: str = typer.Argument(help="Hermes profile name")) -> None:
    """Restart an agent container."""
    agent = _call(lambda progress: controller_factory(progress).restart(agent_name))
    ConsoleProgress().done(f"Restarted {agent.container_name}.")


@app.command()
def shell(agent_name: str = typer.Argument(help="Hermes profile name")) -> None:
    """Open a shell in the agent container at /opt/data."""
    _call(lambda progress: controller_factory(progress).shell(agent_name))


@app.command()
def delete(
    agent_name: str = typer.Argument(help="Hermes profile name"),
    yes: bool = typer.Option(False, "--yes", help="Delete without asking"),
) -> None:
    """Remove the container and delete the agent data."""
    if not yes and not typer.confirm(f"Delete {agent_name}, its container, and its data?"):
        ConsoleProgress().done_error("Delete cancelled.")
        raise typer.Exit(code=1)
    agent = _call(lambda progress: controller_factory(progress).delete(agent_name))
    ConsoleProgress().done(f"Deleted {agent.profile_name}.")


@app.command()
def backup(
    agent_name: str = typer.Argument(help="Hermes profile name"),
    output: Path | None = typer.Option(None, "--output", help="Archive path"),
) -> None:
    """Archive the agent data directory."""
    archive = _call(lambda progress: controller_factory(progress).backup(agent_name, output))
    ConsoleProgress().done(f"Wrote {archive}.")


@app.command()
def restore(
    agent_name: str = typer.Argument(help="Hermes profile name"),
    archive: Path = typer.Argument(help="Archive path"),
) -> None:
    """Replace the agent data directory from an archive."""
    agent = _call(lambda progress: controller_factory(progress).restore(agent_name, archive))
    ConsoleProgress().done(f"Restored {agent.profile_name}.")


def _call(action):
    progress = ConsoleProgress()
    try:
        return action(progress)
    except InstallError as error:
        _fail(progress, error)


def _fail(progress: ConsoleProgress, error: InstallError) -> NoReturn:
    progress.done_error(str(error))
    raise typer.Exit(code=1) from error


def _data_root() -> Path:
    return Path.home() / ".ham"


def _print_table(records: list[AgentRecord]) -> None:
    if not records:
        Console().print("No agents.")
        return
    table = Table()
    table.add_column("Name")
    table.add_column("Container")
    table.add_column("Status")
    table.add_column("Data")
    for record in records:
        table.add_row(record.profile_name, record.container_name, record.status, str(record.data_directory))
    Console().print(table)


def _print_info(record: AgentRecord) -> None:
    console = Console()
    console.print(f"[bold]{record.profile_name}[/bold]")
    console.print(f"Container  {record.container_name}")
    console.print(f"Status     {record.status}")
    console.print(f"Image      {record.image or '-'}")
    console.print(f"Data       {record.data_directory}")


def build_app() -> typer.Typer:
    return app


def run() -> None:
    app()
