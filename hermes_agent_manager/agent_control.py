import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from hermes_agent_manager.agent_name import AgentName
from hermes_agent_manager.agent_paths import find_agent_directories, list_agent_directories
from hermes_agent_manager.archive import extract_archive, write_archive
from hermes_agent_manager.docker_runner import DockerRunner
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.fm_site import FmSite
from hermes_agent_manager.opsai_seed import install_opsai_seed
from hermes_agent_manager.progress import Progress


@dataclass(frozen=True)
class AgentRecord:
    profile_name: str
    container_name: str
    status: str
    data_directory: Path
    image: str
    fm_site: str = ""
    fm_network: str = ""
    hermes_alias: str = ""
    gateway_url: str = ""
    browser_gateway_url: str = ""
    dashboard_user: str = ""
    dashboard_password: str = ""
    dashboard_port: str = ""


class AgentControl:
    def __init__(
        self,
        docker: DockerRunner,
        data_root: Path,
        progress: Progress | None = None,
    ) -> None:
        self._docker = docker
        self._data_root = data_root
        self._progress = progress or Progress()

    def list_agents(self) -> list[AgentRecord]:
        self._docker.ensure_available()
        return [
            self._record_for_directory(path)
            for path in list_agent_directories(self._data_root)
        ]

    def describe(self, raw_name: str, site_name: str | None = None) -> AgentRecord:
        self._docker.ensure_available()
        return self._record_for_agent(self._load_agent(raw_name, site_name))

    def start(self, raw_name: str, site_name: str | None = None) -> AgentName:
        agent = self._require_container(raw_name, site_name)
        self._progress.run(
            f"Starting {agent.container_name}",
            lambda: self._docker.start(agent.container_name),
        )
        return agent

    def stop(self, raw_name: str, site_name: str | None = None) -> AgentName:
        agent = self._require_container(raw_name, site_name)
        self._progress.run(
            f"Stopping {agent.container_name}",
            lambda: self._docker.stop(agent.container_name),
        )
        return agent

    def restart(self, raw_name: str, site_name: str | None = None) -> AgentName:
        agent = self._require_container(raw_name, site_name)
        self._progress.run(
            f"Restarting {agent.container_name}",
            lambda: self._docker.restart(agent.container_name),
        )
        return agent

    def shell(self, raw_name: str, site_name: str | None = None) -> None:
        agent = self._require_container(raw_name, site_name)
        self._docker.shell(agent.container_name)

    def seed(self, raw_name: str, site_name: str | None = None) -> AgentName:
        agent = self._require_running(raw_name, site_name)
        self._progress.run(
            f"Seeding OpsAi files in {agent.container_name}",
            lambda: install_opsai_seed(self._docker, agent.container_name),
        )
        return agent

    def delete(self, raw_name: str, site_name: str | None = None) -> AgentName:
        self._docker.ensure_available()
        agent = self._load_agent(raw_name, site_name)
        directory = self._directory(agent)
        self._ensure_present(agent, directory)
        volume = _read_marker(directory / ".volume")
        self._progress.run(
            f"Removing container {agent.container_name}",
            lambda: self._docker.remove(agent.container_name),
        )
        if volume:
            self._progress.run(
                f"Removing volume {volume}",
                lambda: self._docker.remove_volume(volume),
            )
        self._progress.run(f"Removing {directory}", lambda: _remove_directory(directory))
        _remove_empty_parent(directory.parent)
        return agent

    def backup(
        self,
        raw_name: str,
        destination: Path | None,
        site_name: str | None = None,
    ) -> Path:
        self._docker.ensure_available()
        agent = self._load_agent(raw_name, site_name)
        directory = self._require_directory(agent)
        archive = destination or Path.cwd() / f"{agent.profile_name}.tar.gz"
        self._pause(agent, archive)
        return archive

    def restore(
        self,
        raw_name: str,
        archive: Path,
        site_name: str | None = None,
    ) -> AgentName:
        self._docker.ensure_available()
        agent = self._load_agent(raw_name, site_name)
        if not archive.is_file():
            raise InstallError(f"Archive {archive} does not exist.")
        self._replace(agent, archive)
        return agent

    def _load_agent(self, raw_name: str, site_name: str | None = None) -> AgentName:
        agent = AgentName.parse(raw_name)
        if site_name:
            directory = self._data_root / site_name / agent.profile_name
            if not directory.is_dir():
                raise InstallError(
                    f"Agent {agent.profile_name} not found for site {site_name}."
                )
            site = _read_marker(directory / ".site") or site_name
            return agent.with_site(site)
        matches = find_agent_directories(self._data_root, agent.profile_name)
        if len(matches) > 1:
            sites = ", ".join(path.parent.name for path in matches)
            raise InstallError(
                f"Agent {agent.profile_name} exists on multiple sites ({sites}). "
                f"Pass --site <name>, e.g. ham info {agent.profile_name} --site {matches[0].parent.name}"
            )
        if matches:
            site = _read_marker(matches[0] / ".site") or matches[0].parent.name
            return agent.with_site(site)
        return agent

    def _record_for_directory(self, directory: Path) -> AgentRecord:
        site = _read_marker(directory / ".site") or directory.parent.name
        agent = AgentName.parse(directory.name, site)
        return self._record_for_agent(agent)

    def _record_for_agent(self, agent: AgentName) -> AgentRecord:
        status = self._docker.status(agent.container_name) or "absent"
        image = self._docker.image(agent.container_name) if status != "absent" else ""
        directory = self._directory(agent)
        site_name = agent.site_name or _read_marker(directory / ".site")
        network = FmSite(site_name).network_name if site_name else ""
        gateway = _read_marker(directory / ".gateway_url") or (
            agent.gateway_url if site_name else ""
        )
        port = _read_marker(directory / ".dashboard_port")
        browser = (
            f"http://127.0.0.1:{port}"
            if port
            else (agent.browser_gateway_url if site_name else "")
        )
        return AgentRecord(
            agent.profile_name,
            agent.container_name,
            status,
            directory,
            image,
            site_name,
            network,
            agent.hermes_alias if site_name else "",
            gateway,
            browser,
            _read_marker(directory / ".dashboard_user"),
            _read_marker(directory / ".dashboard_password"),
            port,
        )

    def _pause(self, agent: AgentName, archive: Path) -> None:
        running = self._running(agent)
        if running:
            self._progress.run(
                f"Stopping {agent.container_name}",
                lambda: self._docker.stop(agent.container_name),
            )
        self._progress.run(
            f"Writing {archive}",
            lambda: self._write_backup(agent, archive),
        )
        if running:
            self._progress.run(
                f"Starting {agent.container_name}",
                lambda: self._docker.start(agent.container_name),
            )

    def _write_backup(self, agent: AgentName, archive: Path) -> None:
        directory = self._directory(agent)
        volume = _read_marker(directory / ".volume")
        if not volume:
            write_archive(directory, archive, agent.profile_name)
            return
        with tempfile.TemporaryDirectory() as staging:
            root = Path(staging)
            self._docker.export_volume(volume, str(root), agent.profile_name)
            write_archive(root / agent.profile_name, archive, agent.profile_name)

    def _replace(self, agent: AgentName, archive: Path) -> None:
        running = self._running(agent)
        if running:
            self._progress.run(
                f"Stopping {agent.container_name}",
                lambda: self._docker.stop(agent.container_name),
            )
        if not agent.site_name:
            raise InstallError(
                f"Agent {agent.profile_name} has no site. Create it with ham create first."
            )
        self._progress.run(
            f"Restoring {agent.profile_name}",
            lambda: self._restore_data(agent, archive),
        )
        if running:
            self._progress.run(
                f"Starting {agent.container_name}",
                lambda: self._docker.start(agent.container_name),
            )

    def _restore_data(self, agent: AgentName, archive: Path) -> None:
        directory = self._directory(agent)
        volume = _read_marker(directory / ".volume") if directory.exists() else ""
        if volume:
            with tempfile.TemporaryDirectory() as staging:
                root = Path(staging)
                extract_archive(archive, root, agent.profile_name)
                self._docker.import_volume(volume, str(root), agent.profile_name)
            return
        if directory.exists():
            shutil.rmtree(directory)
        directory.parent.mkdir(parents=True, exist_ok=True)
        extract_archive(archive, directory.parent, agent.profile_name)

    def _running(self, agent: AgentName) -> bool:
        return self._docker.status(agent.container_name) == "running"

    def _require_container(self, raw_name: str, site_name: str | None = None) -> AgentName:
        self._docker.ensure_available()
        agent = self._load_agent(raw_name, site_name)
        if self._docker.container_exists(agent.container_name):
            return agent
        raise InstallError(f"Container {agent.container_name} does not exist.")

    def _require_running(self, raw_name: str, site_name: str | None = None) -> AgentName:
        agent = self._require_container(raw_name, site_name)
        if self._docker.status(agent.container_name) == "running":
            return agent
        raise InstallError(f"Container {agent.container_name} is not running.")

    def _require_directory(self, agent: AgentName) -> Path:
        directory = self._directory(agent)
        if directory.is_dir():
            return directory
        raise InstallError(f"Data directory {directory} does not exist.")

    def _ensure_present(self, agent: AgentName, directory: Path) -> None:
        if self._docker.container_exists(agent.container_name) or directory.exists():
            return
        raise InstallError(f"Agent {agent.profile_name} does not exist.")

    def _directory(self, agent: AgentName) -> Path:
        if agent.site_name:
            return (self._data_root / agent.site_name / agent.profile_name).resolve()
        matches = find_agent_directories(self._data_root, agent.profile_name)
        if matches:
            return matches[0]
        return (self._data_root / agent.profile_name).resolve()


def _remove_directory(directory: Path) -> None:
    if directory.exists():
        shutil.rmtree(directory)


def _remove_empty_parent(directory: Path) -> None:
    if directory.is_dir() and not any(directory.iterdir()):
        directory.rmdir()


def _read_marker(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text().strip()
