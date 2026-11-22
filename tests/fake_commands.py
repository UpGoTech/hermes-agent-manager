import subprocess


class FakeCommands:
    def __init__(self) -> None:
        self.arguments: list[list[str]] = []
        self.existing: set[str] = set()
        self.images: set[str] = set()
        self.volumes: set[str] = set()
        self.networks: set[str] = set()
        self.status = "running"
        self.statuses: dict[str, str] = {}
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
        if arguments[:3] == ["docker", "network", "inspect"]:
            code = 0 if arguments[3] in self.networks else 1
            return self._completed(arguments, code, "")
        if arguments[:3] == ["docker", "volume", "create"]:
            self.volumes.add(arguments[3])
            return self._completed(arguments, 0, "")
        if arguments[:3] == ["docker", "volume", "rm"]:
            self.volumes.discard(arguments[3])
            return self._completed(arguments, 0, "")
        if arguments[:3] == ["docker", "network", "connect"]:
            return self._completed(arguments, 0, "")
        if arguments[:2] == ["docker", "cp"]:
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
            name = arguments[-1]
            status = self.statuses.get(name, self.status)
            if status == "absent":
                return self._completed(arguments, 1, "")
            if "Config.Env" in arguments[3]:
                text = "HERMES_UID=1000\nHERMES_GID=1000\nPATH=/usr/bin\n"
                return self._completed(arguments, 0, text, stderr="")
            if "Image" in arguments[3]:
                text = "ham/hermes-agent:latest\n"
                return self._completed(arguments, 0, text, stderr="")
            return self._completed(arguments, 0, f"{status}\n", stderr="")
        if any("generate_keys" in item for item in arguments):
            return self._completed(
                arguments,
                0,
                "{'api_key': 'key-1', 'api_secret': 'secret-1'}\n",
                stderr="",
            )
        if arguments[:2] == ["docker", "exec"] and "./env/bin/python" in arguments:
            return self._completed(arguments, 0, '{"api_key": "key-1"}\n', stderr="")
        return self._completed(arguments, 0, "")

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
