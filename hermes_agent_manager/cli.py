import os
import sys
from pathlib import Path
from typing import NoReturn

import typer

from hermes_agent_manager.agent_control import AgentControl
from hermes_agent_manager.agent_paths import frappe_agent_root
from hermes_agent_manager.display import (
    print_agent_info,
    print_agent_list,
    print_create_summary,
)
from hermes_agent_manager.docker_runner import IMAGE, DockerRunner
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.fm_site import frappe_manager_home
from hermes_agent_manager.installer import AgentInstaller
from hermes_agent_manager.progress import ConsoleProgress, Progress

app = typer.Typer(add_completion=False, no_args_is_help=True)

_SITE_OPTION = typer.Option(
    None,
    "--site",
    help="FM site when the same agent name exists on more than one site",
)


def installer_factory(progress: Progress) -> AgentInstaller:
    home = frappe_manager_home()
    return AgentInstaller(
        DockerRunner(),
        frappe_agent_root(home),
        os.getuid(),
        os.getgid(),
        progress,
        fm_home=home,
        interactive=sys.stdin.isatty(),
    )


def controller_factory(progress: Progress) -> AgentControl:
    return AgentControl(DockerRunner(), frappe_agent_root(), progress)


@app.command()
def create(
    agent_name: str = typer.Argument(help="Hermes profile name"),
    site: str | None = typer.Option(
        None,
        "--site",
        help="Frappe Manager site name (required when stdin is not a TTY)",
    ),
    user: str | None = typer.Option(
        None,
        "--user",
        "-u",
        help="Hermes dashboard / OpsAi username (prompted when omitted on a TTY)",
    ),
) -> None:
    """Install an agent container linked to an FM site."""
    progress = ConsoleProgress()
    try:
        result = installer_factory(progress).install(agent_name, site, user)
    except InstallError as error:
        _fail(progress, error)
    print_create_summary(
        result.agent,
        result.dashboard_user,
        result.dashboard_password,
        result.data_directory,
    )


@app.command("build-image")
def build_image() -> None:
    """Rebuild the ham workstation image from the packaged Dockerfile."""
    progress = ConsoleProgress()
    try:
        progress.run(
            f"Building {IMAGE}",
            lambda: DockerRunner().build_image(IMAGE, pull=True),
        )
    except InstallError as error:
        _fail(progress, error)
    progress.done(f"Built {IMAGE}.")


@app.command("list")
def list_agents() -> None:
    """List agents."""
    records = _call(lambda progress: controller_factory(progress).list_agents())
    print_agent_list(records)


@app.command()
def info(
    agent_name: str = typer.Argument(help="Hermes profile name"),
    site: str | None = _SITE_OPTION,
) -> None:
    """Show one agent."""
    record = _call(
        lambda progress: controller_factory(progress).describe(agent_name, site)
    )
    print_agent_info(record)


@app.command()
def start(
    agent_name: str = typer.Argument(help="Hermes profile name"),
    site: str | None = _SITE_OPTION,
) -> None:
    """Start an agent container."""
    agent = _call(lambda progress: controller_factory(progress).start(agent_name, site))
    ConsoleProgress().done(f"Started {agent.container_name}.")


@app.command()
def stop(
    agent_name: str = typer.Argument(help="Hermes profile name"),
    site: str | None = _SITE_OPTION,
) -> None:
    """Stop an agent container."""
    agent = _call(lambda progress: controller_factory(progress).stop(agent_name, site))
    ConsoleProgress().done(f"Stopped {agent.container_name}.")


@app.command()
def restart(
    agent_name: str = typer.Argument(help="Hermes profile name"),
    site: str | None = _SITE_OPTION,
) -> None:
    """Restart an agent container."""
    agent = _call(
        lambda progress: controller_factory(progress).restart(agent_name, site)
    )
    ConsoleProgress().done(f"Restarted {agent.container_name}.")


@app.command()
def shell(
    agent_name: str = typer.Argument(help="Hermes profile name"),
    site: str | None = _SITE_OPTION,
) -> None:
    """Open a shell in the agent container at /opt/data."""
    _call(lambda progress: controller_factory(progress).shell(agent_name, site))


@app.command()
def delete(
    agent_name: str = typer.Argument(help="Hermes profile name"),
    site: str | None = _SITE_OPTION,
    yes: bool = typer.Option(False, "--yes", help="Delete without asking"),
) -> None:
    """Remove the container and delete the agent data."""
    label = f"{agent_name} on {site}" if site else agent_name
    if not yes and not typer.confirm(f"Delete {label}, its container, and its data?"):
        ConsoleProgress().done_error("Delete cancelled.")
        raise typer.Exit(code=1)
    agent = _call(lambda progress: controller_factory(progress).delete(agent_name, site))
    ConsoleProgress().done(f"Deleted {agent.profile_name}.")


@app.command()
def backup(
    agent_name: str = typer.Argument(help="Hermes profile name"),
    site: str | None = _SITE_OPTION,
    output: Path | None = typer.Option(None, "--output", help="Archive path"),
) -> None:
    """Archive the agent data directory."""
    archive = _call(
        lambda progress: controller_factory(progress).backup(agent_name, output, site)
    )
    ConsoleProgress().done(f"Wrote {archive}.")


@app.command()
def restore(
    agent_name: str = typer.Argument(help="Hermes profile name"),
    archive: Path = typer.Argument(help="Archive path"),
    site: str | None = _SITE_OPTION,
) -> None:
    """Replace the agent data directory from an archive."""
    agent = _call(
        lambda progress: controller_factory(progress).restore(agent_name, archive, site)
    )
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


def build_app() -> typer.Typer:
    return app


def run() -> None:
    app()
