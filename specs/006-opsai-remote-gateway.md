# OpsAI-compatible remote Hermes gateway

Tracer: expose each ham agent the same way OpsAi talks to Hermes — remote dashboard HTTP + WS — reachable from the FM Frappe container.

## Reachability

OpsAi Desk **Test** and server-side Hermes clients run **inside** the Frappe container.

| URL | Who can use it |
|-----|----------------|
| `http://{site-slug}-{agent}:9119` | Frappe / OpsAi (site network) — **use this in Desk** |
| `http://127.0.0.1:<host-port>` | Mac browser / OpsPilot only |
| `http://host.docker.internal:<host-port>` | Sometimes works from Frappe; flaky under Desk timeouts |

## ham create

1. Dashboard on `0.0.0.0:9119` with basic auth user from `--user` / prompt + generated password.
2. Publish `127.0.0.1:<host-port>:9119` (`host-port = 9119 + crc32({site-slug}-{agent}) % 100`).
3. Label container with compose project `frappe-agents`.
4. `docker network connect --alias {site-slug}-{agent} <site-network> HA-{site-slug}-{agent}`.
5. OpsAi URL: `http://{site-slug}-{agent}:9119`. Print browser URL separately.
6. Refuse create if another marker already claims that host port.

## OpsAi Settings

| Field | Value |
|-------|--------|
| Gateway URL | `http://venus-stm:9119` (example for site `venus.localhost`, agent `stm`) |
| Auth | password / username from `--user` / create password |
