from dataclasses import dataclass
from pathlib import Path

from hermes_agent_manager.agent_name import AgentName
from hermes_agent_manager.agent_paths import agent_data_directory
from hermes_agent_manager.bridge_secret import new_dashboard_password
from hermes_agent_manager.dashboard_port import ensure_host_port_available
from hermes_agent_manager.dashboard_user import parse_dashboard_user
from hermes_agent_manager.docker_runner import CONTAINER_DATA, IMAGE, DockerRunner
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.fm_site import FmSite, pick_site
from hermes_agent_manager.opsai_seed import install_opsai_seed
from hermes_agent_manager.progress import Progress
from hermes_agent_manager.storage import needs_named_volume


@dataclass(frozen=True)
class InstallResult:
    agent: AgentName
    dashboard_user: str
    dashboard_password: str
    data_directory: Path


class AgentInstaller:
    def __init__(
        self,
        docker: DockerRunner,
        data_root: Path,
        user_id: int,
        group_id: int,
        progress: Progress | None = None,
        fm_home: Path | None = None,
        interactive: bool = True,
    ) -> None:
        self._docker = docker
        self._data_root = data_root
        self._user_id = user_id
        self._group_id = group_id
        self._progress = progress or Progress()
        self._fm_home = fm_home
        self._interactive = interactive

    def install(
        self,
        raw_name: str,
        site_name: str | None = None,
        dashboard_user: str | None = None,
    ) -> InstallResult:
        site = pick_site(site_name, self._interactive, self._fm_home)
        agent = AgentName.parse(raw_name, site.name)
        user = parse_dashboard_user(dashboard_user, self._interactive)
        self._ensure_ready(agent, site)
        password = new_dashboard_password()
        self._start(agent, site, user, password)
        return InstallResult(
            agent,
            user,
            password,
            self._directory(agent),
        )

    def _ensure_ready(self, agent: AgentName, site: FmSite) -> None:
        self._docker.ensure_available()
        self._ensure_site_ready(site)
        self._ensure_container_absent(agent)
        self._ensure_directory_absent(agent)
        if needs_named_volume():
            self._ensure_volume_absent(agent)
        ensure_host_port_available(
            self._data_root,
            agent.profile_name,
            agent.dashboard_host_port,
        )

    def _ensure_site_ready(self, site: FmSite) -> None:
        if not self._docker.network_exists(site.network_name):
            raise InstallError(f"FM network {site.network_name} does not exist.")
        if not self._docker.container_exists(site.frappe_container):
            raise InstallError(f"FM container {site.frappe_container} does not exist.")
        if self._docker.status(site.frappe_container) != "running":
            raise InstallError(f"FM container {site.frappe_container} is not running.")

    def _ensure_container_absent(self, agent: AgentName) -> None:
        if not self._docker.container_exists(agent.container_name):
            return
        raise InstallError(f"Container {agent.container_name} already exists.")

    def _ensure_volume_absent(self, agent: AgentName) -> None:
        if not self._docker.volume_exists(agent.volume_name):
            return
        raise InstallError(f"Volume {agent.volume_name} already exists.")

    def _ensure_directory_absent(self, agent: AgentName) -> None:
        path = self._directory(agent)
        if not path.exists():
            return
        raise InstallError(f"Data directory {path} already exists.")

    def _start(
        self,
        agent: AgentName,
        site: FmSite,
        dashboard_user: str,
        dashboard_password: str,
    ) -> None:
        directory = self._directory(agent)
        self._progress.run(f"Ensuring image {IMAGE}", lambda: self._docker.ensure_image(IMAGE))
        if needs_named_volume():
            self._progress.run(
                f"Creating volume {agent.volume_name}",
                lambda: self._docker.ensure_volume(agent.volume_name),
            )
        self._progress.run(
            f"Creating {directory}",
            lambda: self._prepare_directory(agent, site, dashboard_user, dashboard_password),
        )
        self._launch(agent, site, dashboard_user, dashboard_password)

    def _prepare_directory(
        self,
        agent: AgentName,
        site: FmSite,
        dashboard_user: str,
        dashboard_password: str,
    ) -> Path:
        path = self._directory(agent)
        path.mkdir(parents=True)
        (path / ".site").write_text(f"{site.name}\n")
        (path / ".gateway_url").write_text(f"{agent.gateway_url}\n")
        (path / ".dashboard_port").write_text(f"{agent.dashboard_host_port}\n")
        (path / ".dashboard_user").write_text(f"{dashboard_user}\n")
        (path / ".dashboard_password").write_text(f"{dashboard_password}\n")
        if needs_named_volume():
            (path / ".volume").write_text(f"{agent.volume_name}\n")
        return path

    def _directory(self, agent: AgentName) -> Path:
        return agent_data_directory(self._data_root, agent.site_name, agent.profile_name)

    def _launch(
        self,
        agent: AgentName,
        site: FmSite,
        dashboard_user: str,
        dashboard_password: str,
    ) -> None:
        self._progress.run(
            f"Starting container {agent.container_name}",
            lambda: self._start_container(agent, site, dashboard_user, dashboard_password),
        )
        self._progress.run(
            f"Waiting for {agent.container_name}",
            lambda: self._docker.wait_until_running(agent.container_name),
        )
        self._open_profile(agent)
        self._progress.run(
            f"Seeding OpsAi files in {agent.container_name}",
            lambda: install_opsai_seed(
                self._docker,
                agent.container_name,
                {
                    "FM_SITE": site.name,
                    "FRAPPE_URL": f"http://{site.name}",
                    "FRAPPE_URL_USER": f"http://{site.name}",
                },
            ),
        )
        self._progress.run(
            f"Joining network {site.network_name}",
            lambda: self._docker.connect_network(
                site.network_name,
                agent.container_name,
                agent.hermes_alias,
            ),
        )
        self._progress.run(
            f"Recording FM site {site.name}",
            lambda: self._docker.ensure_env(
                agent.container_name,
                {
                    "FM_SITE": site.name,
                    "FRAPPE_URL": f"http://{site.name}",
                    "FRAPPE_URL_USER": f"http://{site.name}",
                    "HERMES_GATEWAY_URL": agent.gateway_url,
                    "HERMES_BROWSER_GATEWAY_URL": agent.browser_gateway_url,
                    "HERMES_DASHBOARD_BASIC_AUTH_USERNAME": dashboard_user,
                    "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD": dashboard_password,
                },
            ),
        )

    def _start_container(
        self,
        agent: AgentName,
        site: FmSite,
        dashboard_user: str,
        dashboard_password: str,
    ) -> None:
        mount = (
            agent.volume_name
            if needs_named_volume()
            else str(self._directory(agent))
        )
        self._docker.run_gateway(
            agent.container_name,
            mount,
            self._user_id,
            self._group_id,
            IMAGE,
            agent.profile_name,
            site.name,
            dashboard_user,
            dashboard_password,
            agent.dashboard_host_port,
            agent.gateway_url,
        )

    def _open_profile(self, agent: AgentName) -> None:
        self._progress.run(
            f"Creating profile {agent.profile_name} in {agent.container_name} at {CONTAINER_DATA}",
            lambda: self._docker.create_profile(agent.container_name, agent.profile_name),
        )
