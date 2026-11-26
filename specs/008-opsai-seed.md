# OpsAi seed on create

Tracer: every `ham create` installs OpsAi Hermes home files into `/opt/data`, and `ham seed` re-applies them on an existing agent.

## Files (packaged under `hermes_agent_manager/seed/`)

| Source | Destination in container |
|--------|--------------------------|
| `SOUL.md` | `/opt/data/SOUL.md` |
| `memories/MEMORY.md` | `/opt/data/memories/MEMORY.md` |
| `memories/USER.md` | `/opt/data/memories/USER.md` |
| `skills/erpnext/SKILL.md` | `/opt/data/skills/erpnext/SKILL.md` |
| `skills/erpnext/scripts/frappe.py` | `/opt/data/skills/erpnext/scripts/frappe.py` |

Also enables `memory.memory_enabled` and `memory.user_profile_enabled` via `hermes config set`.

## `.env` keys (from `seed/env.example`)

Appended to `/opt/data/.env` only when the key is missing:

- `FRAPPE_URL`, `FRAPPE_URL_USER`, `FRAPPE_API_KEY`, `FRAPPE_API_SECRET`, `FM_SITE`

`ham create` overrides `FRAPPE_URL`, `FRAPPE_URL_USER`, and `FM_SITE` with the FM site. API key placeholders stay until the operator fills them in.

## Behavior

1. `ham create` copies those files into the running container after the profile exists (works for bind mount and named volume).
2. `ham seed <agent-name> [--site <fm-site>]` does the same for an older agent whose container is running.
3. Overwrites existing SOUL / MEMORY / USER / erpnext skill files. No backup (operator can `ham backup` first).
4. Never overwrites an existing `.env` key.

## Out of scope

- Shipping `install.sh` / zip README as the install path
- Auto-provisioning Frappe API tokens

## Related

Remote resolution via `opsai-seed-v*` tags: [009-remote-opsai-seed.md](009-remote-opsai-seed.md).
