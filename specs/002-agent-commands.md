# Agent commands

`ham create <agent-name> --site <fm-site> --user <name>` is the install command. The other commands manage that agent. Names follow [001-install-agent.md](001-install-agent.md): container `HA-{site-slug}-{agent}`, data `~/frappe/frappe-agent/<site>/<agent>/`, profile `{agent}`.

| Command | Action |
|---------|--------|
| `create` | Ensure `ham/hermes-agent:latest`, install container/profile, then seed OpsAi SOUL + erpnext skill (`--seed-ref` optional) |
| `build-image` | Force-rebuild `ham/hermes-agent:latest` with `--pull` |
| `list` | FM-style table: Agent, Status (Active/Inactive), FM Site, OpsAi Gateway |
| `info` | Show one agent in an FM-style Rich table (status, image, volume, gateway URLs, dashboard user, compose group) |
| `create` (summary) | After steps, print OpsAi Gateway, Browser Gateway, Username, Password for Desk setup |
| `start` | `docker start HA-{site-slug}-{agent}` |
| `stop` | `docker stop HA-{site-slug}-{agent}` |
| `restart` | `docker restart HA-{site-slug}-{agent}` |
| `shell` | `docker exec -it --user hermes` at `/opt/data`; prompt is `hermes@<agent-name>.localhost` |
| `seed` | Copy OpsAi `SOUL.md` and `erpnext` skill into a running agent (`/opt/data`); optional `--seed-ref` (see [009](009-remote-opsai-seed.md)) |
| `delete` | Remove container and `~/frappe/frappe-agent/<site>/<agent>/` |
| `backup` | Write a gzip archive of the data directory. Stop a running container first, then start it again |
| `restore` | Replace the data directory from an archive. Stop a running container first, then start it again |

`delete` asks for confirmation unless `--yes` is passed. Commands that need a container fail when it does not exist. `backup` and `restore` need the data directory or the archive, and they do not call the Hermes install on the host.

Frappe Manager commands that do not apply here are left out: `code`, `ssl`, `ngrok`, `services`, `self`, `migrate`, and `reset`.
