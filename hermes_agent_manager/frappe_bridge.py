import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

from hermes_agent_manager.agent_name import AgentName
from hermes_agent_manager.docker_runner import DockerRunner
from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.fm_site import FmSite


@dataclass(frozen=True)
class FrappeCredentials:
    api_key: str
    api_secret: str
    email: str


class FrappeBridge:
    def __init__(self, docker: DockerRunner) -> None:
        self._docker = docker

    def ensure_site_ready(self, site: FmSite) -> None:
        if not self._docker.network_exists(site.network_name):
            raise InstallError(f"FM network {site.network_name} does not exist.")
        if not self._docker.container_exists(site.frappe_container):
            raise InstallError(f"FM container {site.frappe_container} does not exist.")
        if self._docker.status(site.frappe_container) != "running":
            raise InstallError(f"FM container {site.frappe_container} is not running.")

    def provision(
        self,
        agent: AgentName,
        site: FmSite,
        bridge_secret: str,
        app_source: Path,
    ) -> FrappeCredentials:
        email = f"ham+{agent.profile_name}@localhost"
        self._create_user(site, agent.profile_name, email)
        credentials = self._generate_keys(site, email)
        self._install_app(site, app_source)
        self._register_agent(site, agent, email, bridge_secret)
        return credentials

    def _create_user(self, site: FmSite, username: str, email: str) -> None:
        script = (
            "import frappe\n"
            f"if not frappe.db.exists('User', '{email}'):\n"
            "    user = frappe.get_doc({\n"
            "        'doctype': 'User',\n"
            f"        'email': '{email}',\n"
            f"        'first_name': '{username}',\n"
            f"        'username': '{username}',\n"
            "        'send_welcome_email': 0,\n"
            "    })\n"
            "    user.append('roles', {'role': 'System Manager'})\n"
            "    user.insert(ignore_permissions=True)\n"
            "    frappe.db.commit()\n"
        )
        self._execute(site, script)

    def _generate_keys(self, site: FmSite, email: str) -> FrappeCredentials:
        output = self._docker.frappe_execute(
            site.frappe_container,
            site.name,
            "frappe.core.doctype.user.user.generate_keys",
            f"['{email}']",
        )
        secret = _parse_api_secret(output)
        key = self._read_api_key(site, email)
        return FrappeCredentials(key, secret, email)

    def _read_api_key(self, site: FmSite, email: str) -> str:
        script = (
            "import frappe, json\n"
            f"print(json.dumps({{'api_key': frappe.db.get_value('User', '{email}', 'api_key')}}))\n"
        )
        output = self._execute(site, script)
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("{"):
                payload = json.loads(line)
                key = payload.get("api_key")
                if key:
                    return key
        raise InstallError(f"Could not read api_key for {email}.")

    def _install_app(self, site: FmSite, app_source: Path) -> None:
        self._docker.copy_to_container(
            site.frappe_container,
            str(app_source),
            "/workspace/frappe-bench/apps/ham_bridge",
        )
        self._docker.frappe_bench(
            site.frappe_container,
            ["pip", "install", "-e", "apps/ham_bridge"],
        )
        try:
            self._docker.frappe_bench(
                site.frappe_container,
                ["--site", site.name, "install-app", "ham_bridge"],
            )
        except InstallError as error:
            if "already installed" not in str(error).lower():
                raise

    def _register_agent(
        self,
        site: FmSite,
        agent: AgentName,
        email: str,
        bridge_secret: str,
    ) -> None:
        alias = agent.hermes_alias
        script = (
            "import frappe\n"
            f"name = '{agent.profile_name}'\n"
            "if frappe.db.exists('Ham Agent', name):\n"
            "    doc = frappe.get_doc('Ham Agent', name)\n"
            "else:\n"
            "    doc = frappe.new_doc('Ham Agent')\n"
            "    doc.agent_name = name\n"
            f"doc.user = '{email}'\n"
            f"doc.hermes_alias = '{alias}'\n"
            f"doc.bridge_secret = '{bridge_secret}'\n"
            f"doc.ticket_url = 'http://{alias}:8650/ticket'\n"
            f"doc.ws_url = 'ws://{alias}:8642/api/ws'\n"
            "doc.save(ignore_permissions=True)\n"
            "frappe.db.commit()\n"
        )
        self._execute(site, script)

    def _execute(self, site: FmSite, script: str) -> str:
        return self._docker.frappe_execute_script(site.frappe_container, site.name, script)


def _parse_api_secret(output: str) -> str:
    for line in output.splitlines():
        line = line.strip()
        if "api_secret" in line and line.startswith("{"):
            payload = ast.literal_eval(line)
            secret = payload.get("api_secret")
            if secret:
                return secret
    match = re.search(r"'api_secret':\s*'([^']+)'", output)
    if match:
        return match.group(1)
    match = re.search(r'"api_secret":\s*"([^"]+)"', output)
    if match:
        return match.group(1)
    raise InstallError("Could not parse Frappe API secret.")
