# Progress

Specs: [001](specs/001-install-agent.md), [002](specs/002-agent-commands.md), [003](specs/003-workstation-image.md), [004](specs/004-frappe-agent-data.md), [005](specs/005-fm-bridge.md), [006](specs/006-opsai-remote-gateway.md), [007](specs/007-developer-mode.md), [008](specs/008-opsai-seed.md), [009](specs/009-remote-opsai-seed.md)

| Phase | Status |
|-------|--------|
| Spec | Done |
| Package (`pyproject.toml`, `ham` entry point) | Done |
| Install (`HA-<name>` container, profile `<name>`, detached gateway) | Done |
| Tests (fake Docker runner) | Done |
| README reconciliation | Done |
| Install the `ham` command with uv | Done |
| Host gateway serves the named profile; show install steps | Done |
| Commands: create, list, info, start, stop, restart, shell, delete, backup, restore | Done |
| Workstation image (`ham/hermes-agent`, build on create, `build-image`) | Done (beta) |
| Named volume for `/opt/data` (retired) | Replaced |
| Host data under `~/frappe/frappe-agent/<site>/<agent>` bind mount | Done (beta) |
| FM site bind via host reverse proxy (Hermes → Frappe) | Done (beta) |
| OpsAi-compatible remote dashboard (per-agent host port) | Done (beta) |
| Dashboard user from `ham create --user` (no fixed `ham`) | Done (beta) |
| Compose project group `frappe-agents` | Done (beta) |
| Container `HA-{site-slug}-{agent}` | Done (beta) |
| `ham info` FM-style Rich table | Done (beta) |
| Developer mode (`--developer`, site workspace + bench sidecar) | Planned |
| OpsAi seed on create (`SOUL` / memory / erpnext skill) + `ham seed` | Done (beta) |
| Remote OpsAi seed via `opsai-seed-v*` tags (same repo) | Spec |
