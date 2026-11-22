import re
from dataclasses import dataclass, replace

from hermes_agent_manager.dashboard_port import host_dashboard_port
from hermes_agent_manager.errors import InstallError

_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_INVALID = (
    "Agent name must start with a letter or digit and contain only "
    "letters, digits, dots, underscores, and hyphens."
)
_LOCALHOST_SUFFIX = ".localhost"


@dataclass(frozen=True)
class AgentName:
    value: str
    site_name: str = ""

    @classmethod
    def parse(cls, raw: str, site_name: str = "") -> "AgentName":
        if _PATTERN.fullmatch(raw) is None:
            raise InstallError(_INVALID)
        return cls(raw, site_name)

    def with_site(self, site_name: str) -> "AgentName":
        return replace(self, site_name=site_name)

    @property
    def site_slug(self) -> str:
        name = self.site_name
        if name.endswith(_LOCALHOST_SUFFIX):
            name = name[: -len(_LOCALHOST_SUFFIX)]
        return name.replace(".", "-")

    @property
    def identity(self) -> str:
        if not self.site_slug:
            return self.value
        return f"{self.site_slug}-{self.value}"

    @property
    def container_name(self) -> str:
        if not self.site_slug:
            return f"HA-{self.value}"
        return f"HA-{self.site_slug}-{self.value}"

    @property
    def profile_name(self) -> str:
        return self.value

    @property
    def volume_name(self) -> str:
        if not self.site_slug:
            return f"ham-{self.value}"
        return f"ham-{self.site_slug}-{self.value}"

    @property
    def hermes_alias(self) -> str:
        return self.identity

    @property
    def dashboard_host_port(self) -> int:
        return host_dashboard_port(self.identity)

    @property
    def gateway_url(self) -> str:
        return f"http://{self.hermes_alias}:9119"

    @property
    def browser_gateway_url(self) -> str:
        return f"http://127.0.0.1:{self.dashboard_host_port}"
