import os
from dataclasses import dataclass
from pathlib import Path

from hermes_agent_manager.errors import InstallError


@dataclass(frozen=True)
class FmSite:
    name: str

    @property
    def slug(self) -> str:
        return self.name.replace(".", "_")

    @property
    def network_name(self) -> str:
        return f"fm__{self.slug}__network"

    @property
    def frappe_container(self) -> str:
        return f"fm__{self.slug}__frappe"


def frappe_manager_home() -> Path:
    raw = os.environ.get("FRAPPE_MANAGER_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / "frappe"


def list_sites(home: Path | None = None) -> list[FmSite]:
    root = (home or frappe_manager_home()) / "sites"
    if not root.is_dir():
        return []
    sites = []
    for path in sorted(root.iterdir()):
        if path.is_dir() and (path / "docker-compose.yml").is_file():
            sites.append(FmSite(path.name))
    return sites


def require_sites(home: Path | None = None) -> list[FmSite]:
    sites = list_sites(home)
    if sites:
        return sites
    root = home or frappe_manager_home()
    raise InstallError(
        f"No Frappe Manager sites found under {root / 'sites'}. "
        "Create a site with fm first."
    )


def resolve_site(name: str | None, home: Path | None = None) -> FmSite:
    sites = require_sites(home)
    if name is None:
        raise InstallError(_site_choice_message(sites))
    for site in sites:
        if site.name == name:
            return site
    raise InstallError(
        f"Unknown FM site {name}. Available: {', '.join(site.name for site in sites)}"
    )


def pick_site(name: str | None, interactive: bool, home: Path | None = None) -> FmSite:
    sites = require_sites(home)
    if name is not None:
        return resolve_site(name, home)
    if not interactive:
        raise InstallError(_site_choice_message(sites))
    return _prompt_site(sites)


def _site_choice_message(sites: list[FmSite]) -> str:
    listed = ", ".join(site.name for site in sites)
    return f"Pass --site <name>. Available FM sites: {listed}"


def _prompt_site(sites: list[FmSite]) -> FmSite:
    print("Select an FM site:")
    for index, site in enumerate(sites, start=1):
        print(f"  {index}. {site.name}")
    raw = input("Site number: ").strip()
    try:
        choice = int(raw)
    except ValueError as error:
        raise InstallError("Site selection must be a number.") from error
    if choice < 1 or choice > len(sites):
        raise InstallError(f"Site number must be between 1 and {len(sites)}.")
    return sites[choice - 1]
