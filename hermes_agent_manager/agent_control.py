import shutil
from dataclasses import dataclass
from pathlib import Path

from hermes_agent_manager.agent_name import AgentName
from hermes_agent_manager.archive import extract_archive, write_archive
from hermes_agent_manager.docker_runner import DockerRunner
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.progress import Progress


@dataclass(frozen=True)
class AgentRecord:
    profile_name: str
    container_name: str
    status: str
    data_directory: Path
    image: str


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
        return [self.describe(name) for name in self._profile_names()]

    def describe(self, raw_name: str) -> AgentRecord:
        self._docker.ensure_available()
        agent = AgentName.parse(raw_name)
        status = self._docker.status(agent.container_name) or "absent"
        image = self._docker.image(agent.container_name) if status != "absent" else ""
        return AgentRecord(
            agent.profile_name,
            agent.container_name,
            status,
            self._directory(agent),
            image,
        )

    def start(self, raw_name: str) -> AgentName:
        agent = self._require_container(raw_name)
        self._progress.run(
            f"Starting {agent.container_name}",
            lambda: self._docker.start(agent.container_name),
        )
        return agent

    def stop(self, raw_name: str) -> AgentName:
        agent = self._require_container(raw_name)
        self._progress.run(
            f"Stopping {agent.container_name}",
            lambda: self._docker.stop(agent.container_name),
        )
        return agent

    def restart(self, raw_name: str) -> AgentName:
        agent = self._require_container(raw_name)
        self._progress.run(
            f"Restarting {agent.container_name}",
            lambda: self._docker.restart(agent.container_name),
        )
        return agent

    def shell(self, raw_name: str) -> None:
        agent = self._require_container(raw_name)
        self._docker.shell(agent.container_name)

    def delete(self, raw_name: str) -> AgentName:
        self._docker.ensure_available()
        agent = AgentName.parse(raw_name)
        directory = self._directory(agent)
        self._ensure_present(agent, directory)
        self._progress.run(
            f"Removing container {agent.container_name}",
            lambda: self._docker.remove(agent.container_name),
        )
        self._progress.run(f"Removing {directory}", lambda: _remove_directory(directory))
        return agent

    def backup(self, raw_name: str, destination: Path | None) -> Path:
        self._docker.ensure_available()
        agent = AgentName.parse(raw_name)
        directory = self._require_directory(agent)
        archive = destination or directory.with_suffix(".tar.gz")
        self._pause(agent, directory, archive)
        return archive

    def restore(self, raw_name: str, archive: Path) -> AgentName:
        self._docker.ensure_available()
        agent = AgentName.parse(raw_name)
        if not archive.is_file():
            raise InstallError(f"Archive {archive} does not exist.")
        self._replace(agent, archive)
        return agent

    def _pause(self, agent: AgentName, directory: Path, archive: Path) -> None:
        running = self._running(agent)
        if running:
            self._progress.run(
                f"Stopping {agent.container_name}",
                lambda: self._docker.stop(agent.container_name),
            )
        self._progress.run(
            f"Writing {archive}",
            lambda: write_archive(directory, archive, agent.profile_name),
        )
        if running:
            self._progress.run(
                f"Starting {agent.container_name}",
                lambda: self._docker.start(agent.container_name),
            )

    def _replace(self, agent: AgentName, archive: Path) -> None:
        running = self._running(agent)
        if running:
            self._progress.run(
                f"Stopping {agent.container_name}",
                lambda: self._docker.stop(agent.container_name),
            )
        directory = self._directory(agent)
        if directory.exists():
            shutil.rmtree(directory)
        self._progress.run(
            f"Restoring {directory}",
            lambda: extract_archive(archive, self._data_root, agent.profile_name),
        )
        if running:
            self._progress.run(
                f"Starting {agent.container_name}",
                lambda: self._docker.start(agent.container_name),
            )

    def _running(self, agent: AgentName) -> bool:
        return self._docker.status(agent.container_name) == "running"

    def _require_container(self, raw_name: str) -> AgentName:
        self._docker.ensure_available()
        agent = AgentName.parse(raw_name)
        if self._docker.container_exists(agent.container_name):
            return agent
        raise InstallError(f"Container {agent.container_name} does not exist.")

    def _require_directory(self, agent: AgentName) -> Path:
        directory = self._directory(agent)
        if directory.is_dir():
            return directory
        raise InstallError(f"Data directory {directory} does not exist.")

    def _ensure_present(self, agent: AgentName, directory: Path) -> None:
        exists = self._docker.container_exists(agent.container_name) or directory.exists()
        if exists:
            return
        raise InstallError(f"Agent {agent.profile_name} does not exist.")

    def _directory(self, agent: AgentName) -> Path:
        return self._data_root / agent.profile_name

    def _profile_names(self) -> list[str]:
        if not self._data_root.is_dir():
            return []
        names = [path.name for path in self._data_root.iterdir() if path.is_dir()]
        return sorted(name for name in names if _valid_name(name))


def _remove_directory(directory: Path) -> None:
    if directory.exists():
        shutil.rmtree(directory)


def _valid_name(name: str) -> bool:
    try:
        AgentName.parse(name)
    except InstallError:
        return False
    return True
