# FM site binding (Hermes → Frappe via reverse proxy)

Tracer bullet: `ham create` requires an FM site and routes HTTP to that site the same way the host browser does — through Frappe Manager's `global-nginx-proxy` on the host.

Bench + site workspace for developer agents is separate: [007-developer-mode.md](007-developer-mode.md).

```bash
ham create stm --site venus.localhost --user alice
```

1. List FM sites under `$FRAPPE_MANAGER_HOME/sites` or `~/frappe/sites`. Refuse create if none.
2. Resolve `--site` / `--user` or interactive prompts.
3. Require the site's `fm__<site>__frappe` container to be running.
4. Create data dir/container/profile with site-aware names (`HA-venus-stm`, `~/frappe/frappe-agent/venus.localhost/stm/`).
5. `docker run --add-host <site>:host-gateway` so `venus.localhost` points at the host (where FM publishes :80/:443).
6. Env: `FM_SITE=<site>`, `FRAPPE_URL=http://<site>`.
7. Join `fm__<site>__network` with alias `venus-stm` (Frappe → Hermes / OpsAi Desk Test).
8. Write the same into `/opt/data/.env`.

## Reachability

Host path: browser/`curl http://venus.localhost` → host :80 → `fm_global-nginx-proxy` → site nginx → frappe.

Inside the agent container, Python and most resolvers honor `--add-host` and hit that proxy. Curl special-cases `*.localhost` to loopback (RFC 6761); the image bashrc wraps `curl` with `--resolve` to the host gateway so `curl http://venus.localhost` matches the host browser.

## Tests

- Create argv includes `--add-host <site>:host-gateway` and `FRAPPE_URL=http://<site>`
- Create `docker network connect`s the site network with alias `{site-slug}-{agent}`
- `.site` marker written
