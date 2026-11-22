# Frappe-agent host data (bind mount)

Tracer: store all agent data under the Frappe Manager home, next to `sites/`, and bind-mount it into the container at `/opt/data`.

```text
$FRAPPE_MANAGER_HOME/   # or ~/frappe
  sites/
  frappe-agent/
    venus.localhost/
      purchase/          # -> /opt/data
```

## Behavior

1. Root is `frappe_manager_home() / "frappe-agent"` (macOS, Linux, WSL via `pathlib` + `$FRAPPE_MANAGER_HOME`).
2. Agent directory is `frappe-agent/<site-name>/<agent-name>/`.
3. `ham create` creates that directory and writes markers (`.site`, `.gateway_url`, `.dashboard_user`, `.dashboard_password`, `.dashboard_port`).
4. **Runtime mount for `/opt/data`:**
   - **macOS / WSL:** Docker named volume `ham-<site-slug>-<agent>` (virtiofs bind mounts cannot `chmod 600` on `gateway.sock`). Marker `.volume` records the name.
   - **Linux:** bind-mount the agent directory (native ext4 supports sockets).
5. No `~/.ham`.
6. `ham list` walks `frappe-agent/*/*`. `ham delete` removes the container, named volume (if any), and the agent directory.
7. `ham backup` / `ham restore` use the host dir on Linux, or export/import the named volume on macOS/WSL.

## Platforms

Unix CLI only (same as FM): macOS, Linux, WSL. Inside WSL use the Linux home path, not `C:\...`.

## Out of scope

- Migrating old `~/.ham`-only agents (delete + recreate)
