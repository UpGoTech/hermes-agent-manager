# Developer mode (site-scoped bench + filesystem)

Tracer: `ham create <agent> --site <fm-site> --user <name> --developer`
gives one Hermes agent bench + apps filesystem access for **that FM site only**,
without mounting the host Docker socket into Hermes.

Normal agents stay HTTP/API-only. Developer agents never receive raw
`/var/run/docker.sock`.

Related: [005-fm-bridge.md](005-fm-bridge.md) (HTTP + site network),
[004-frappe-agent-data.md](004-frappe-agent-data.md) (agent data mounts),
[003-workstation-image.md](003-workstation-image.md) (image tools).

## Goal topology (example)

One Docker host, two FM sites, nine Hermes agents:

| Count | Flag | Site | Access |
|------:|------|------|--------|
| 4 | (default) | mars.localhost | HTTP/API only |
| 2 | (default) | venus.localhost | HTTP/API only |
| 1 | `--developer` | mars.localhost | HTTP + site workspace FS + bench sidecar |
| 2 | `--developer` | venus.localhost | HTTP + site workspace FS + bench sidecar |

Cross-site bench, workspace, and Docker control must be denied by construction
(mounts, networks, sidecar allowlist) — not by trusting the model.

## Behavior

1. `ham create` gains optional `--developer` (default off).
2. Refuse `--developer` unless the FM site exists, `fm__<slug>__frappe` is
   running, and `~/frappe/sites/<site>/workspace` exists (FM bind source for
   `/workspace` inside frappe).
3. Developer create still does everything normal create does (data dir,
   gateway, site network alias, OpsAi URL, markers).
4. **Extra mounts (Hermes container only):**
   - Bind `sites/<site>/workspace` → `/workspace` (read-write).
   - Optionally narrower later: only `frappe-bench/apps` — start with full
     workspace so diagnose (logs, sites config) works.
5. **Bench sidecar** (started with the developer agent, same compose project
   `frappe-agents`):
   - Name e.g. `HA-<site-slug>-<agent>-bench` (or `ham-bench-<site-slug>-<agent>`).
   - Mounts **only** `/var/run/docker.sock` (Hermes does not).
   - Env hard-coded: `FM_FRAPPE_CONTAINER=fm__<slug>__frappe`, `FM_SITE=<site>`,
     allowlist of argv prefixes (e.g. `bench …` under
     `/workspace/frappe-bench` as user `frappe`).
   - Exposes a small HTTP API on the **site network only** (not published to
     host), alias e.g. `<site-slug>-<agent>-bench`.
   - Hermes calls that API; sidecar runs
     `docker exec --user frappe --workdir /workspace/frappe-bench <container> …`.
6. Record markers under the agent dir: `.developer`, `.bench_url`,
   `.frappe_workspace` (paths/URLs for `ham info` / recreate).
7. `ham delete` removes Hermes **and** its sidecar.
8. `ham info` shows Developer: yes/no, workspace path, bench helper URL.
9. **Do not** install a Frappe custom app for bench mediation (`ham_bridge`
   stays tickets/gateway only).

## Trust boundary

```text
Hermes --developer
  ├─ site network → Frappe HTTP (same as normal)
  ├─ bind → sites/<site>/workspace          # FS for that site only
  └─ HTTP → bench sidecar (site network)
                └─ docker.sock → exec ONLY fm__<that_site>__frappe
```

| Actor | docker.sock | Other site workspace | Other site frappe exec |
|-------|-------------|----------------------|-------------------------|
| Normal Hermes | No | No | No |
| Developer Hermes | No | No | No |
| That agent's sidecar | Yes | No | No (single container name) |

## Isolation notes (non-goals vs mitigations)

- **Absolute** “AI cannot break out” is not promised (shared kernel, leaked
  keys, Docker bugs). Spec targets **default deny** across sites.
- Same-site peer agents on one FM network may still reach each other’s
  aliases; cross-site Docker networks stay separate.
- Host reverse proxy / host-gateway may still allow TCP to another site’s
  HTTP front door; without that site’s credentials that is not admin access.
  Follow-up (optional phase): prefer site-network-only `FRAPPE_URL` and avoid
  advertising host-gateway as a general egress tip inside developer shells.
- Sidecar allowlist must reject arbitrary `docker`, `sh -c`, and container
  name overrides from the client.

## CLI / UX

```bash
ham create appdev --site mars.localhost --user alice --developer
```

Print after create (in addition to OpsAi lines):

- Workspace: `/workspace` → host `…/sites/mars.localhost/workspace`
- Bench helper: `http://mars-appdev-bench:<port>` (internal)
- Reminder: no host Docker socket inside Hermes

## Implementation sketch (when coding)

- `cli.py` — `--developer` flag on create
- `docker_runner.py` — gateway argv extras (workspace mount); sidecar run/rm
- `installer.py` / `agent_control.py` — lifecycle + markers + info rows
- New small image or same `ham/hermes-agent` entrypoint mode for sidecar
  (prefer tiny dedicated image later; tracer may reuse python:slim + docker CLI)
- Tests with fake Docker runner: normal create has no sock/workspace/sidecar;
  developer create has workspace mount, sidecar with sock + fixed container
  env, Hermes argv has no sock

## Tracer phases

1. Spec + PROGRESS row (this doc).
2. `--developer` create: workspace bind + markers + info only (no bench yet).
3. Sidecar MVP: allowlisted `bench` argv → `docker exec` one container; Hermes
   env `BENCH_HELPER_URL`.
4. Delete/info/restart lifecycle for sidecar.
5. Harden allowlist + optional site-network-only HTTP follow-up.
6. README reconciliation.

## Out of scope (v1)

- Raw docker.sock in Hermes (rejected Option A for multi-agent hosts)
- Frappe app that shells out to bench
- Interactive TTY proxy through sidecar (phase 2+; start with exec + capture)
- Cross-site developer dual-mount
- Publishing bench helper on host ports
