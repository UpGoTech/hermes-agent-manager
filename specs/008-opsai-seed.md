# OpsAi seed on create

Tracer: every `ham create` installs OpsAi Hermes home files into `/opt/data`, and `ham seed` re-applies them on an existing agent.

## Files (repo `opsai-seed/`, fetched via GitHub seed tags)

| Source | Destination in container |
|--------|--------------------------|
| `SOUL.md` | `/opt/data/SOUL.md` |
| `skills/erpnext/SKILL.md` | `/opt/data/skills/erpnext/SKILL.md` |
| `skills/erpnext/scripts/frappe.py` | `/opt/data/skills/erpnext/scripts/frappe.py` |

Not packaged inside the ham wheel. Default `.env` keys come from `default_env_values()` in HAM.

## `.env` keys (static in HAM)

Appended to `/opt/data/.env` only when the key is missing:

- `FRAPPE_URL`, `FRAPPE_URL_USER`, `FRAPPE_API_KEY`, `FRAPPE_API_SECRET`, `FM_SITE`

`ham create` overrides `FRAPPE_URL`, `FRAPPE_URL_USER`, and `FM_SITE` with the FM site. API key placeholders stay until the operator fills them in.

## Behavior

1. `ham create` / `ham seed` fetch the seed pack from GitHub (`opsai-seed-v*`), then copy into the running container.
2. Overwrites existing SOUL / erpnext skill files. No backup (operator can `ham backup` first).
3. Never overwrites an existing `.env` key.

## Out of scope

- Shipping seed files inside the ham package / `--seed-ref bundled`
- Auto-provisioning Frappe API tokens
- Seeding `memories/`

## Related

Remote resolution: [009-remote-opsai-seed.md](009-remote-opsai-seed.md).
