# MEMORY — OpsAi / Hermes environment

## Frappe connection
- Base URL: `FRAPPE_URL` (internal; never show to user). Public URL: `FRAPPE_URL_USER` (always show to user).
- Auth: `Authorization: token $FRAPPE_API_KEY:$FRAPPE_API_SECRET` (token auth, not password).
- Apps: ERPNext, Saral HR, CRM. Site: `FM_SITE`.
- Reach Frappe only over HTTP via `FRAPPE_URL`. No DB, bench, docker exec, SSH, sockets, or port probing. If it fails, report; don't hunt.
- REST API: `/api/resource/<DocType>`, `/api/method/<method>`, `/api/resource/<DocType>/<name>`. List filters are JSON arrays, e.g. `[["status","=","Open"]]`.
- Writes: verify by re-reading the document before claiming success. Submit via `frappe.client.submit`; cancel via `frappe.client.cancel`.
- Never expose internal URL/IP/port/container names. Links to the user use `FRAPPE_URL_USER`.

## Workspace / delivery
- Hermes home: `$HERMES_HOME` (default `/opt/data`). Write deliverables under the workspace and include the absolute path in the reply.
- OpsAi shows Preview/Download only when it sees the absolute path. For HTML, also emit `::preview` on its own line with the real path.
- Interactive dashboards: one self-contained .html file (data/CSS/JS inlined); OpsAi preview cannot call ERPNext APIs from that tab.
- No cloudflared/ngrok/local servers/public tunnels.
- HTML/PDF: use frappe-ui tokens and typography. PDFs: self-contained HTML + browser print, A4 portrait; never reportlab/fpdf.
- The `erpnext` skill has the REST helper script; use it instead of hand-rolling requests.

## Memory maintenance
- Keep this file under ~3000 chars. When near the limit, consolidate or replace entries; do not append indefinitely.
