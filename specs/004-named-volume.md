# Named data volume (beta)

Tracer bullet: put `/opt/data` on a Docker named volume so `gateway.sock` can be mode `0600`.

## Why

Docker Desktop (virtiofs) bind mounts accept Unix sockets but reject `chmod 600` (`EINVAL`), leaving `gateway.sock` at `0755`. Hermes then refuses the CLI with `unsafe_control_permissions`. Hermes docs recommend a named volume on virtiofs for the same reason (WAL/sqlite).

## Behavior

1. Volume name is `ham-<agent-name>` (same charset rules as the agent name).
2. `ham create` runs `docker volume create ham-<agent-name>` when missing, mounts it at `/opt/data`, and still creates marker dir `~/.ham/<agent-name>/` (for `list` / identity).
3. No host bind mount of the full data tree.
4. `ham delete` removes the container, the volume, and the marker dir.
5. `ham backup` / `ham restore` copy through a short-lived Alpine container into/out of the volume, keeping the existing tar layout (`<agent-name>/...`).
6. Edit `.env` and configs with `ham shell` (path `/opt/data/.env`).

## Out of scope

- Migrating existing bind-mounted agents (delete + recreate)
- Publishing a host bind for `.env` only
