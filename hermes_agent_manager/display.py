from pathlib import Path

from rich.console import Console
from rich.table import Table

from hermes_agent_manager.agent_control import AgentRecord
from hermes_agent_manager.agent_name import AgentName


def print_agent_list(records: list[AgentRecord], console: Console | None = None) -> None:
    out = console or Console()
    if not records:
        out.print("No agents.")
        return
    table = Table(show_lines=True, highlight=True)
    table.add_column("Agent")
    table.add_column("Status")
    table.add_column("FM Site")
    table.add_column("OpsAi Gateway")
    for record in records:
        table.add_row(
            record.profile_name,
            list_status(record.status),
            record.fm_site or "N/A",
            record.gateway_url or "N/A",
        )
    out.print(table)


def print_agent_info(record: AgentRecord, console: Console | None = None) -> None:
    print_key_value(info_rows(record), console)


def print_create_summary(
    agent: AgentName,
    dashboard_user: str,
    dashboard_password: str,
    marker: Path,
    console: Console | None = None,
) -> None:
    out = console or Console()
    out.print(f"[green]✓[/green] Created agent [bold]{agent.profile_name}[/bold]")
    print_key_value(
        [
            ("Agent", agent.profile_name),
            ("Container", agent.container_name),
            ("FM Site", agent.site_name or "N/A"),
            ("OpsAi Gateway", agent.gateway_url),
            ("Browser Gateway", agent.browser_gateway_url),
            ("Username", dashboard_user),
            ("Password", dashboard_password),
            ("Data", str(marker)),
        ],
        out,
    )
    out.print(
        "Desk → OpsAi Settings: use [bold]OpsAi Gateway[/bold] with "
        "[bold]Username[/bold] / [bold]Password[/bold]. "
        "Browser Gateway is for local browser access only."
    )


def print_key_value(rows: list[tuple[str, str]], console: Console | None = None) -> None:
    out = console or Console()
    table = Table(show_lines=True, show_header=False, highlight=True)
    table.add_column(no_wrap=True)
    table.add_column(no_wrap=True)
    for label, value in rows:
        table.add_row(label, value)
    out.print(table)


def info_rows(record: AgentRecord) -> list[tuple[str, str]]:
    return [
        ("Agent", record.profile_name),
        ("Container", record.container_name),
        ("Status", detail_status(record.status)),
        ("Image", record.image or "N/A"),
        ("FM Site", record.fm_site or "N/A"),
        ("FM Network", record.fm_network or "N/A"),
        ("Network Alias", record.hermes_alias or "N/A"),
        ("OpsAi Gateway", record.gateway_url or "N/A"),
        ("Dashboard User", record.dashboard_user or "N/A"),
        ("Password", record.dashboard_password or "N/A"),
        ("Host Port", record.dashboard_port or "N/A"),
        ("Data", str(record.data_directory)),
        ("Compose Group", "frappe-agents"),
    ]


def list_status(status: str) -> str:
    if status == "running":
        return "[green]Active[/green]"
    if status == "absent":
        return "[red]Absent[/red]"
    return "[red]Inactive[/red]"


def detail_status(status: str) -> str:
    if status == "running":
        return "[green]Active[/green]"
    if status == "absent":
        return "[red]Absent[/red]"
    if not status:
        return "N/A"
    return f"[red]{status.replace('_', ' ').title()}[/red]"
