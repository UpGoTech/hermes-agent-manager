import subprocess
from typing import Protocol


class CommandRunner(Protocol):
    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        pass


class SubprocessCommandRunner:
    def run(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(arguments, capture_output=True, text=True)
