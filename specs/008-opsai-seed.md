# OpsAi seed on create

Tracer: every `ham create` installs OpsAi Hermes home files into `/opt/data`, and `ham seed` re-applies them on an existing agent.

## Files (under `hermes_agent_manager/seed/`, also via remote tags)

| Source | Destination in container |
|--------|--------------------------|
| `SOUL.md` | `/opt/data/SOUL.md` |
| `skills/erpnext/SKILL.md` | `/opt/data/skills/erpnext/SKILL.md` |
| `skills/erpnext/scripts/frappe.py` | `/opt/data/skills/erpnext/scripts/frappe.py` |

Memories are not seeded. Default `.env` keys come from `default_env_values()` in the HAM tool (not from the seed tree).

## `.env` keys (static in HAM)

Appended to `/opt/data/.env` only when the key is missing:

- `FRAPPE_URL`, `FRAPPE_URL_USER`, `FRAPPE_API_KEY`, `FRAPPE_API_SECRET`, `FM_SITE`

`ham create` overrides `FRAPPE_URL`, `FRAPPE_URL_USER`, and `FM_SITE` with the FM site. API key placeholders stay until the operator fills them in.

## Behavior

1. `ham create` copies those files into the running container after the profile exists (works for bind mount and named volume).
2. `ham seed <agent-name> [--site <fm-site>]` does the same for an older agent whose container is running.
3. Overwrites existing SOUL / erpnext skill files. No backup (operator can `ham backup` first).
4. Never overwrites an existing `.env` key.

## Out of scope

- Shipping `install.sh` / zip README as the install path
- Auto-provisioning Frappe API tokens
- Seeding `memories/` or shipping `env.example` in the seed pack

## Related

Remote resolution via `opsai-seed-v*` tags: [009-remote-opsai-seed.md](009-remote-opsai-seed.md).
