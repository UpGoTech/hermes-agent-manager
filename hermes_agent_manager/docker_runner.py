import shutil
import subprocess
import time
from collections.abc import Callable

from hermes_agent_manager.commands import CommandRunner, SubprocessCommandRunner
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.image import build_context

IMAGE = "ham/hermes-agent:latest"
CONTAINER_DATA = "/opt/data"
SHELL_USER = "hermes"


class DockerRunner:
    def __init__(
        self,
        commands: CommandRunner | None = None,
        available: Callable[[], bool] | None = None,
        sleep: Callable[[float], None] | None = None,
        attempts: int = 30,
        attached: Callable[[list[str]], int] | None = None,
    ) -> None:
        self._commands = commands or SubprocessCommandRunner()
        self._available = available or _docker_on_path
        self._sleep = sleep or time.sleep
        self._attempts = attempts
        self._attached = attached or _attached_run

    def ensure_available(self) -> None:
        if self._available():
            return
        raise InstallError("Docker is not available. Install Docker and try again.")

    def pull(self, image: str) -> None:
        self._check(["docker", "pull", image])

    def image_exists(self, image: str) -> bool:
        completed = self._commands.run(["docker", "image", "inspect", image])
        return completed.returncode == 0

    def build_image(self, image: str, context: str | None = None, pull: bool = False) -> None:
        arguments = ["docker", "build", "-t", image]
        if pull:
            arguments.append("--pull")
        arguments.append(context or str(build_context()))
        self._check(arguments)

    def ensure_image(self, image: str) -> None:
        if self.image_exists(image):
            return
        self.build_image(image)

    def container_exists(self, name: str) -> bool:
        completed = self._commands.run(["docker", "container", "inspect", name])
        return completed.returncode == 0

    def run_gateway(
        self,
        container_name: str,
        host_path: str,
        user_id: int,
        group_id: int,
        image: str,
        agent_name: str,
    ) -> None:
        self._check(
            _gateway_arguments(
                container_name,
                host_path,
                user_id,
                group_id,
                image,
                agent_name,
            )
        )

    def wait_until_running(self, container_name: str) -> None:
        for _ in range(self._attempts):
            if self._status(container_name) == "running":
                return
            self._sleep(1)
        raise InstallError(f"Container {container_name} did not start.")

    def create_profile(self, container_name: str, profile_name: str) -> None:
        arguments = _profile_arguments(container_name, profile_name)
        last_error = ""
        for _ in range(self._attempts):
            completed = self._commands.run(arguments)
            if completed.returncode == 0:
                return
            last_error = _command_error(completed, arguments)
            self._sleep(1)
        raise InstallError(last_error)

    def status(self, container_name: str) -> str:
        return self._status(container_name)

    def image(self, container_name: str) -> str:
        completed = self._commands.run(_image_arguments(container_name))
        if completed.returncode != 0:
            return ""
        return completed.stdout.strip()

    def start(self, container_name: str) -> None:
        self._check(["docker", "start", container_name])

    def stop(self, container_name: str) -> None:
        self._check(["docker", "stop", container_name])

    def restart(self, container_name: str) -> None:
        self._check(["docker", "restart", container_name])

    def remove(self, container_name: str) -> None:
        if not self.container_exists(container_name):
            return
        self._check(["docker", "rm", "-f", container_name])

    def shell(self, container_name: str) -> None:
        code = self._attached(_shell_arguments(container_name))
        if code == 0:
            return
        raise InstallError(f"Shell in {container_name} exited with status {code}.")

    def _status(self, container_name: str) -> str:
        completed = self._commands.run(_status_arguments(container_name))
        if completed.returncode != 0:
            return ""
        return completed.stdout.strip()

    def _check(self, arguments: list[str]) -> None:
        completed = self._commands.run(arguments)
        if completed.returncode == 0:
            return
        raise InstallError(_command_error(completed, arguments))


def _docker_on_path() -> bool:
    return shutil.which("docker") is not None


def _attached_run(arguments: list[str]) -> int:
    return subprocess.run(arguments).returncode


def _gateway_arguments(
    container_name: str,
    host_path: str,
    user_id: int,
    group_id: int,
    image: str,
    agent_name: str,
) -> list[str]:
    return [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "--hostname",
        _agent_hostname(agent_name),
        "--restart",
        "unless-stopped",
        "-v",
        f"{host_path}:/opt/data",
        "-e",
        f"HERMES_UID={user_id}",
        "-e",
        f"HERMES_GID={group_id}",
        "-e",
        f"HERMES_HOME={CONTAINER_DATA}",
        "-e",
        f"HAM_AGENT={agent_name}",
        image,
        "gateway",
        "run",
    ]


def _status_arguments(container_name: str) -> list[str]:
    return ["docker", "inspect", "--format", "{{.State.Status}}", container_name]


def _image_arguments(container_name: str) -> list[str]:
    return ["docker", "inspect", "--format", "{{.Config.Image}}", container_name]


def _shell_arguments(container_name: str) -> list[str]:
    return _exec_arguments(container_name, interactive=True) + ["bash"]


def _profile_arguments(container_name: str, profile_name: str) -> list[str]:
    return _exec_arguments(container_name) + [
        "hermes",
        "profile",
        "create",
        profile_name,
    ]


def _exec_arguments(container_name: str, interactive: bool = False) -> list[str]:
    arguments = ["docker", "exec"]
    if interactive:
        arguments.append("-it")
    arguments.extend(
        [
            "--user",
            SHELL_USER,
            "--workdir",
            CONTAINER_DATA,
            "-e",
            f"HERMES_HOME={CONTAINER_DATA}",
            container_name,
        ]
    )
    return arguments


def _agent_hostname(agent_name: str) -> str:
    return f"{agent_name}.localhost"


def _command_error(completed: subprocess.CompletedProcess[str], arguments: list[str]) -> str:
    detail = "\n".join(
        part for part in (completed.stderr.strip(), completed.stdout.strip()) if part
    )
    return detail or f"Docker command failed: {' '.join(arguments)}"
