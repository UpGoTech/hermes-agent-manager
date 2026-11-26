# Hermes Agent Manager

Command-line tool for installing and managing Hermes agents linked to Frappe Manager sites.

Pass the agent name as a CLI argument. That name becomes the Hermes profile. The container is `HA-{site-without-.localhost}-{agent-name}`. Many agents may share one FM site. Containers are labeled under the Docker Compose project `frappe-agents`.

Supported hosts: **macOS**, **Linux**, and **WSL** (run inside the Linux environment, not native Windows Python).

## Purpose

`ham create` requires an existing FM site. Hermes reaches that site over HTTP the same way your browser does: through FM's host reverse proxy (`http://venus.localhost` → host :80 → `global-nginx-proxy`).

For Hermes the other way, ham joins the FM site network as `{site}-{agent}` and runs the Hermes dashboard on container port `9119` (also published to a per-agent host port for browsers). OpsAi Desk Test must use the site-network URL.

## Data layout

Markers and metadata live next to FM sites (same home as Frappe Manager):

```text
~/frappe/                    # or $FRAPPE_MANAGER_HOME
  sites/
  frappe-agent/
    venus.localhost/
      purchase/              # markers; Linux also bind-mounts this to /opt/data
```

On **macOS / WSL**, Hermes `/opt/data` uses a Docker named volume (`ham-<site>-<agent>`) because Docker Desktop virtiofs cannot `chmod 600` on `gateway.sock`. On **Linux**, the host directory is bind-mounted.

On WSL use the Linux home path (e.g. `/home/<user>/frappe/...`), not `C:\Users\...`.

## Install

Requires Python 3.11 or newer, [uv](https://docs.astral.sh/uv/), Docker, and at least one FM site under `~/frappe/sites` (or `$FRAPPE_MANAGER_HOME/sites`).

From the released tag (anyone):

```bash
uv tool install git+https://github.com/UpGoTech/hermes-agent-manager@v1.0.2
ham build-image
```

From a local checkout:

```bash
rm -rf build && uv tool install --force --reinstall .
ham build-image
```

## Usage

```bash
ham create <agent-name> --site <fm-site> --user <dashboard-user>
```

Omit `--site` / `--user` on an interactive TTY to pick the site and enter the dashboard username.

### Example

```bash
ham create stm --site venus.localhost --user alice
```

This will:

1. Require FM site `venus.localhost` (frappe container running)
2. Ensure `ham/hermes-agent:latest` exists
3. Create `~/frappe/frappe-agent/venus.localhost/stm/` (markers + Hermes home)
4. Start `HA-venus-stm` with that directory bind-mounted at `/opt/data`
5. Create Hermes profile `stm`
6. Seed OpsAi `SOUL.md` and `erpnext` skill into `/opt/data` (latest `opsai-seed-v*` tag, or packaged fallback); fill missing `.env` keys from HAM defaults
7. Join site network as `venus-stm` and print OpsAi credentials

### OpsAi Settings (Desk Test)

| Field | Value |
|-------|--------|
| Gateway URL | `http://venus-stm:9119` (from `ham info` / create) |
| Auth mode | password |
| Username | the `--user` / prompted value |
| Password | printed at end of `ham create` (also in `ham info`) |

Browser gateway `http://127.0.0.1:<port>` is for local browsers only.

## What gets set for you

| Setting        | Value                                      |
|----------------|--------------------------------------------|
| Container name | `HA-{site-slug}-{agent-name}`              |
| Profile name   | CLI argument (`<agent-name>`)              |
| Data directory | `~/frappe/frappe-agent/<site>/<agent>/`    |
| Compose group  | `frappe-agents`                            |
| FM site        | `--site` / interactive pick                |
| Dashboard user | `--user` / interactive prompt              |
| Gateway (OpsAi)| `http://{site-slug}-{agent}:9119`          |
| Image          | `ham/hermes-agent:latest`                  |

`site-slug` is the FM site name with `.localhost` stripped (e.g. `venus.localhost` → `venus`).

## Commands

| Command | Action |
|---------|--------|
| `ham create <agent-name> --site <fm-site> --user <name>` | Install agent linked to an FM site |
| `ham build-image` | Rebuild `ham/hermes-agent:latest` with `--pull` |
| `ham list` | List agents and container status |
| `ham info <agent-name>` | Show agent details (FM-style table) |
| `ham start <agent-name>` | Start the container |
| `ham stop <agent-name>` | Stop the container |
| `ham restart <agent-name>` | Restart the container |
| `ham shell <agent-name>` | Open a `hermes` user shell at `/opt/data` |
| `ham seed <agent-name>` | Install OpsAi SOUL + erpnext skill into a running agent |
| `ham seed <agent-name> --seed-ref opsai-seed-v1.0.0` | Seed a pinned GitHub tag (also on `create`; `bundled` / `latest` allowed) |
| `ham delete <agent-name>` | Remove container and data directory |
| `ham backup <agent-name>` | Archive the data directory |
| `ham restore <agent-name> <archive>` | Restore the data directory from an archive |

## OpsAi seed tags

Seed content lives in `hermes_agent_manager/seed/`. Publish content without a HAM release:

```bash
git tag opsai-seed-v1.0.0
git push origin opsai-seed-v1.0.0
```

`ham create` / `ham seed` default to the newest `opsai-seed-v*` tag (cache in `~/.ham/seed-cache/`). App tags stay `v*`. Use `--seed-ref bundled` offline, or pin an older seed tag when needed. Override repo with `HAM_SEED_REPO`.

## Migration

Old installs used `~/.ham` markers + Docker named volumes. Delete those agents and recreate under `frappe-agent/`.

## Status

Beta on `beta/workstation-image`. Rebuild the image after pulling changes (`ham build-image`).
