# Hermes Agent Manager

Command-line tool for installing and managing Hermes agents on a VPS with sensible defaults.

Pass the agent name as a CLI argument. That name becomes the Hermes profile. The container is the same name with an `HA-` prefix.

## Purpose

If you want Hermes agent running on a VPS, you do not need to hand-configure Docker, image tags, or profile setup. Run this tool, supply the agent name, and the rest uses default parameters for a standard VPS deployment.

On the `beta/workstation-image` branch, `ham create` builds a local workstation image (`ham/hermes-agent:latest`) on top of the official Hermes image. That adds shell tools (`vim`, `jq`, `tree`, `sudo`, …) and a richer bash prompt for `ham shell`, similar to Frappe Manager's fat image.

## Install

Requires Python 3.11 or newer, and [uv](https://docs.astral.sh/uv/).

From a checkout of this repository:

```bash
uv tool install .
```

`uv` installs the `ham` command into its tool bin directory, usually `~/.local/bin`.

## Usage

```bash
ham create <agent-name>
```

### Example

```bash
ham create my-agent
```

This will:

1. Ensure `ham/hermes-agent:latest` exists (build it from the packaged Dockerfile if missing; Docker pulls `nousresearch/hermes-agent:latest` as the base)
2. Create `~/.ham/my-agent` and mount it at `/opt/data`
3. Start detached container `HA-my-agent` with `gateway run` and `--restart unless-stopped`
4. Create Hermes profile `my-agent` inside the container at `/opt/data`. A Hermes install on the host is not used. The container gateway serves that profile.

Host ports are not published, and the dashboard stays off. API keys are not prompted. Add them later in `~/.ham/my-agent/.env`. The image reads that file from `/opt/data/.env`.

Rebuild the workstation image after package updates:

```bash
ham build-image
```

## What gets set for you

| Setting        | Value                                      |
|----------------|--------------------------------------------|
| Container name | `HA-<agent-name>`                          |
| Profile name   | CLI argument (`<agent-name>`)              |
| Data directory | `~/.ham/<agent-name>`                      |
| Image          | `ham/hermes-agent:latest` (FROM official)  |
| Command        | `gateway run`                              |
| Restart        | `unless-stopped`                           |
| Ports          | not published                              |
| Dashboard      | off                                        |

The container runs as the current user id and group id (`HERMES_UID`, `HERMES_GID`).

## Requirements

- A VPS (or host) with Docker available
- Network access to pull the official Hermes agent image (base for the ham build)
- Permission to build images and run containers

## Commands

| Command | Action |
|---------|--------|
| `ham create <agent-name>` | Install the container and profile |
| `ham build-image` | Rebuild `ham/hermes-agent:latest` with `--pull` |
| `ham list` | List agents and container status |
| `ham info <agent-name>` | Show container, status, image, and data directory |
| `ham start <agent-name>` | Start the container |
| `ham stop <agent-name>` | Stop the container |
| `ham restart <agent-name>` | Restart the container |
| `ham shell <agent-name>` | Open a shell as `HERMES_UID` at `/opt/data` |
| `ham delete <agent-name>` | Remove the container and delete its data |
| `ham backup <agent-name>` | Archive the data directory |
| `ham restore <agent-name> <archive>` | Replace the data directory from an archive |

`delete` asks before it removes anything. Pass `--yes` to skip the question. `backup` writes `~/.ham/<agent-name>.tar.gz` unless `--output` is set. A running container is stopped for backup and restore, then started again.

## Status

These commands cover the agent lifecycle. The install does not start the interactive setup wizard.
