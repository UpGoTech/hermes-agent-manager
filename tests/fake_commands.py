import re
import subprocess
from pathlib import Path

from hermes_agent_manager.docker_runner import ARCHIVE_IMAGE


class FakeCommands:
    def __init__(self) -> None:
        self.arguments: list[list[str]] = []
        self.existing: set[str] = set()
        self.images: set[str] = set()
        self.volumes: set[str] = set()
        self.status = "running"
        self.failures: dict[str, str] = {}

    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        self.arguments.append(list(arguments))
        if arguments[:3] == ["docker", "container", "inspect"]:
            code = 0 if arguments[3] in self.existing else 1
            return self._completed(arguments, code, "")
        if arguments[:3] == ["docker", "image", "inspect"]:
            code = 0 if arguments[3] in self.images else 1
            return self._completed(arguments, code, "")
        if arguments[:3] == ["docker", "volume", "inspect"]:
            code = 0 if arguments[3] in self.volumes else 1
            return self._completed(arguments, code, "")
        if arguments[:3] == ["docker", "volume", "create"]:
            self.volumes.add(arguments[3])
            return self._completed(arguments, 0, "")
        if arguments[:3] == ["docker", "volume", "rm"]:
            self.volumes.discard(arguments[3])
            return self._completed(arguments, 0, "")
        if arguments[:2] == ["docker", "build"]:
            if self._failed(arguments):
                return self._completed(arguments, 1, self.failures["build"])
            tag = arguments[arguments.index("-t") + 1]
            self.images.add(tag)
            return self._completed(arguments, 0, "")
        if self._failed(arguments):
            return self._completed(arguments, 1, self.failures[arguments[1]])
        if arguments[:3] == ["docker", "inspect", "--format"]:
            if self.status == "absent":
                return self._completed(arguments, 1, "")
            if "Config.Env" in arguments[3]:
                text = "HERMES_UID=1000\nHERMES_GID=1000\nPATH=/usr/bin\n"
                return self._completed(arguments, 0, text, stderr="")
            if "Image" in arguments[3]:
                text = "ham/hermes-agent:latest\n"
                return self._completed(arguments, 0, text, stderr="")
            return self._completed(arguments, 0, f"{self.status}\n", stderr="")
        if ARCHIVE_IMAGE in arguments:
            self._stage_archive_transfer(arguments)
            return self._completed(arguments, 0, "")
        return self._completed(arguments, 0, "")

    def _stage_archive_transfer(self, arguments: list[str]) -> None:
        mounts = _volume_mounts(arguments)
        script = arguments[-1]
        match = re.search(r"/to/([A-Za-z0-9_.-]+)", script)
        if match and "/from" in mounts and "/to" in mounts:
            destination = Path(mounts["/to"]) / match.group(1)
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "note.txt").write_text("hello")


    def _failed(self, arguments: list[str]) -> bool:
        return len(arguments) > 1 and arguments[1] in self.failures

    def _completed(
        self,
        arguments: list[str],
        code: int,
        stdout: str,
        stderr: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        error = "" if stderr is not None else stdout
        return subprocess.CompletedProcess(arguments, code, stdout, stderr or error)


def _volume_mounts(arguments: list[str]) -> dict[str, str]:
    mounts: dict[str, str] = {}
    index = 0
    while index < len(arguments):
        if arguments[index] == "-v" and index + 1 < len(arguments):
            host, _, remainder = arguments[index + 1].partition(":")
            target = remainder.split(":", 1)[0]
            mounts[target] = host
            index += 2
            continue
        index += 1
    return mounts
