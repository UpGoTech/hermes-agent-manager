from pathlib import Path

from hermes_agent_manager.agent_name import AgentName
from hermes_agent_manager.docker_runner import CONTAINER_DATA, IMAGE, DockerRunner
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.progress import Progress


class AgentInstaller:
    def __init__(
        self,
        docker: DockerRunner,
        data_root: Path,
        user_id: int,
        group_id: int,
        progress: Progress | None = None,
    ) -> None:
        self._docker = docker
        self._data_root = data_root
        self._user_id = user_id
        self._group_id = group_id
        self._progress = progress or Progress()

    def install(self, raw_name: str) -> AgentName:
        agent = AgentName.parse(raw_name)
        self._ensure_ready(agent)
        self._start(agent)
        return agent

    def _ensure_ready(self, agent: AgentName) -> None:
        self._docker.ensure_available()
        self._ensure_container_absent(agent)
        self._ensure_volume_absent(agent)
        self._ensure_marker_absent(agent)

    def _ensure_container_absent(self, agent: AgentName) -> None:
        if not self._docker.container_exists(agent.container_name):
            return
        raise InstallError(f"Container {agent.container_name} already exists.")

    def _ensure_volume_absent(self, agent: AgentName) -> None:
        if not self._docker.volume_exists(agent.volume_name):
            return
        raise InstallError(f"Volume {agent.volume_name} already exists.")

    def _ensure_marker_absent(self, agent: AgentName) -> None:
        path = self._marker_directory(agent)
        if not path.exists():
            return
        raise InstallError(f"Data directory {path} already exists.")

    def _start(self, agent: AgentName) -> None:
        self._progress.run(f"Ensuring image {IMAGE}", lambda: self._docker.ensure_image(IMAGE))
        self._progress.run(
            f"Creating volume {agent.volume_name}",
            lambda: self._docker.ensure_volume(agent.volume_name),
        )
        self._progress.run(
            f"Creating {self._marker_directory(agent)}",
            lambda: self._prepare_marker(agent),
        )
        self._launch(agent)

    def _prepare_marker(self, agent: AgentName) -> Path:
        path = self._marker_directory(agent)
        path.mkdir(parents=True)
        (path / ".volume").write_text(f"{agent.volume_name}\n")
        return path

    def _marker_directory(self, agent: AgentName) -> Path:
        return self._data_root / agent.profile_name

    def _launch(self, agent: AgentName) -> None:
        self._progress.run(
            f"Starting container {agent.container_name}",
            lambda: self._start_container(agent),
        )
        self._progress.run(
            f"Waiting for {agent.container_name}",
            lambda: self._docker.wait_until_running(agent.container_name),
        )
        self._open_profile(agent)

    def _start_container(self, agent: AgentName) -> None:
        self._docker.run_gateway(
            agent.container_name,
            agent.volume_name,
            self._user_id,
            self._group_id,
            IMAGE,
            agent.profile_name,
        )

    def _open_profile(self, agent: AgentName) -> None:
        self._progress.run(
            f"Creating profile {agent.profile_name} in {agent.container_name} at {CONTAINER_DATA}",
            lambda: self._docker.create_profile(agent.container_name, agent.profile_name),
        )
