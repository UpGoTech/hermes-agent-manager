import re
from dataclasses import dataclass

from hermes_agent_manager.errors import InstallError

_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_INVALID = (
    "Agent name must start with a letter or digit and contain only "
    "letters, digits, dots, underscores, and hyphens."
)


@dataclass(frozen=True)
class AgentName:
    value: str

    @classmethod
    def parse(cls, raw: str) -> "AgentName":
        if _PATTERN.fullmatch(raw) is None:
            raise InstallError(_INVALID)
        return cls(raw)

    @property
    def container_name(self) -> str:
        return f"HA-{self.value}"

    @property
    def profile_name(self) -> str:
        return self.value

    @property
    def volume_name(self) -> str:
        return f"ham-{self.value}"
