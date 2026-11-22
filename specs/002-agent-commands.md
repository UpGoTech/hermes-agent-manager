# Agent commands

`ham create <agent-name>` is the install command. The other commands manage that agent. Names, container prefix, and `/opt/data` stay as in [001-install-agent.md](001-install-agent.md).

| Command | Action |
|---------|--------|
| `create` | Ensure `ham/hermes-agent:latest`, then install container `HA-<agent-name>` and profile `<agent-name>` |
| `build-image` | Force-rebuild `ham/hermes-agent:latest` with `--pull` |
| `list` | Show each agent under `~/.ham` with container status |
| `info` | Show one agent's container, status, image, and data directory |
| `start` | `docker start HA-<agent-name>` |
| `stop` | `docker stop HA-<agent-name>` |
| `restart` | `docker restart HA-<agent-name>` |
| `shell` | `docker exec -it` a shell in `HA-<agent-name>` at `/opt/data` with `HERMES_HOME=/opt/data` |
| `delete` | Remove container `HA-<agent-name>` and delete `~/.ham/<agent-name>` |
| `backup` | Write a gzip archive of the data directory. Stop a running container first, then start it again |
| `restore` | Replace the data directory from an archive. Stop a running container first, then start it again |

`delete` asks for confirmation unless `--yes` is passed. Commands that need a container fail when `HA-<agent-name>` does not exist. `backup` and `restore` need the data directory or the archive, and they do not call the Hermes install on the host.

Frappe Manager commands that do not apply here are left out: `code`, `ssl`, `ngrok`, `services`, `self`, `migrate`, and `reset`.
