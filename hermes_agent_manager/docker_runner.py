import shlex
import shutil
import subprocess
import time
from collections.abc import Callable

from hermes_agent_manager.commands import CommandRunner, SubprocessCommandRunner
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.image import build_context

from hermes_agent_manager.dashboard_port import COMPOSE_PROJECT, CONTAINER_DASHBOARD_PORT

IMAGE = "ham/hermes-agent:latest"
CONTAINER_DATA = "/opt/data"
SHELL_USER = "hermes"
ARCHIVE_IMAGE = "alpine:3.20"


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

    def volume_exists(self, name: str) -> bool:
        completed = self._commands.run(["docker", "volume", "inspect", name])
        return completed.returncode == 0

    def ensure_volume(self, name: str) -> None:
        if self.volume_exists(name):
            return
        self._check(["docker", "volume", "create", name])

    def remove_volume(self, name: str) -> None:
        if not self.volume_exists(name):
            return
        self._check(["docker", "volume", "rm", name])

    def network_exists(self, name: str) -> bool:
        completed = self._commands.run(["docker", "network", "inspect", name])
        return completed.returncode == 0

    def connect_network(self, network_name: str, container_name: str, alias: str) -> None:
        self._check(
            [
                "docker",
                "network",
                "connect",
                "--alias",
                alias,
                network_name,
                container_name,
            ]
        )

    def copy_to_container(self, container_name: str, source: str, destination: str) -> None:
        self._check(["docker", "cp", source, f"{container_name}:{destination}"])

    def frappe_execute(
        self,
        container_name: str,
        site_name: str,
        method: str,
        args: str,
    ) -> str:
        completed = self._commands.run(
            _frappe_exec_arguments(
                container_name,
                [
                    "bench",
                    "--site",
                    site_name,
                    "execute",
                    method,
                    "--args",
                    args,
                ],
            )
        )
        if completed.returncode != 0:
            raise InstallError(_command_error(completed, ["frappe", "execute", method]))
        return completed.stdout + completed.stderr

    def frappe_execute_script(self, container_name: str, site_name: str, script: str) -> str:
        prelude = (
            "import frappe\n"
            f"frappe.init(site={site_name!r})\n"
            "frappe.connect()\n"
        )
        payload = prelude + script + "\nfrappe.destroy()\n"
        completed = self._commands.run(
            _frappe_exec_arguments(
                container_name,
                ["./env/bin/python", "-c", payload],
            )
        )
        if completed.returncode != 0:
            raise InstallError(_command_error(completed, ["frappe", "python", "-c"]))
        return completed.stdout + completed.stderr

    def frappe_bench(self, container_name: str, arguments: list[str]) -> None:
        self._check(_frappe_exec_arguments(container_name, ["bench", *arguments]))

    def append_env(self, container_name: str, values: dict[str, str]) -> None:
        lines = "".join(f"{key}={value}\n" for key, value in values.items())
        script = (
            "mkdir -p /opt/data && "
            "touch /opt/data/.env && "
            f"printf %s {shlex.quote(lines)} >> /opt/data/.env"
        )
        self._check(
            [
                "docker",
                "exec",
                "--user",
                "root",
                container_name,
                "sh",
                "-c",
                script,
            ]
        )

    def run_gateway(
        self,
        container_name: str,
        data_mount: str,
        user_id: int,
        group_id: int,
        image: str,
        agent_name: str,
        site_name: str,
        dashboard_user: str,
        dashboard_password: str,
        host_port: int,
        gateway_url: str,
    ) -> None:
        self._check(
            _gateway_arguments(
                container_name,
                data_mount,
                user_id,
                group_id,
                image,
                agent_name,
                site_name,
                dashboard_user,
                dashboard_password,
                host_port,
                gateway_url,
            )
        )

    def export_volume(self, volume_name: str, host_directory: str, profile_name: str) -> None:
        self._check(_export_volume_arguments(volume_name, host_directory, profile_name))

    def import_volume(self, volume_name: str, host_directory: str, profile_name: str) -> None:
        self.ensure_volume(volume_name)
        self._check(_import_volume_arguments(volume_name, host_directory, profile_name))

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
    data_mount: str,
    user_id: int,
    group_id: int,
    image: str,
    agent_name: str,
    site_name: str,
    dashboard_user: str,
    dashboard_password: str,
    host_port: int,
    gateway_url: str,
) -> list[str]:
    return [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "--hostname",
        _agent_hostname(agent_name),
        "--label",
        f"com.docker.compose.project={COMPOSE_PROJECT}",
        "--label",
        f"com.docker.compose.service={container_name}",
        "--label",
        "com.docker.compose.container-number=1",
        "--add-host",
        f"{site_name}:host-gateway",
        "-p",
        f"127.0.0.1:{host_port}:{CONTAINER_DASHBOARD_PORT}",
        "--restart",
        "unless-stopped",
        "-v",
        f"{data_mount}:{CONTAINER_DATA}",
        "-e",
        f"HERMES_UID={user_id}",
        "-e",
        f"HERMES_GID={group_id}",
        "-e",
        f"HERMES_HOME={CONTAINER_DATA}",
        "-e",
        f"HAM_AGENT={agent_name}",
        "-e",
        f"FM_SITE={site_name}",
        "-e",
        f"FRAPPE_URL=http://{site_name}",
        "-e",
        f"HERMES_GATEWAY_URL={gateway_url}",
        "-e",
        "HERMES_DASHBOARD=1",
        "-e",
        "HERMES_DASHBOARD_HOST=0.0.0.0",
        "-e",
        f"HERMES_DASHBOARD_PORT={CONTAINER_DASHBOARD_PORT}",
        "-e",
        f"HERMES_DASHBOARD_BASIC_AUTH_USERNAME={dashboard_user}",
        "-e",
        f"HERMES_DASHBOARD_BASIC_AUTH_PASSWORD={dashboard_password}",
        image,
        "gateway",
        "run",
    ]


def _frappe_exec_arguments(container_name: str, command: list[str]) -> list[str]:
    return [
        "docker",
        "exec",
        "--user",
        "frappe",
        "--workdir",
        "/workspace/frappe-bench",
        container_name,
        *command,
    ]


def _export_volume_arguments(volume_name: str, host_directory: str, profile_name: str) -> list[str]:
    script = (
        f"mkdir -p /to/{profile_name} && "
        f"cp -a /from/. /to/{profile_name}/"
    )
    return [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{volume_name}:/from:ro",
        "-v",
        f"{host_directory}:/to",
        ARCHIVE_IMAGE,
        "sh",
        "-c",
        script,
    ]


def _import_volume_arguments(volume_name: str, host_directory: str, profile_name: str) -> list[str]:
    script = (
        "rm -rf /to/* /to/.[!.]* /to/..?* 2>/dev/null; "
        f"cp -a /from/{profile_name}/. /to/"
    )
    return [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{volume_name}:/to",
        "-v",
        f"{host_directory}:/from:ro",
        ARCHIVE_IMAGE,
        "sh",
        "-c",
        script,
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
