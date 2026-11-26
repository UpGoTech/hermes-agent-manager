# Remote OpsAi seed (same repo, separate tags)

Tracer: `ham create` / `ham seed` resolve OpsAi seed content from this GitHub repo via **seed tags**. Content lives at repo-root `opsai-seed/` (not inside the Python package).

## Tag contract

| Kind | Pattern | Example |
|------|---------|---------|
| App release | `v*` | `v1.0.2` |
| Seed pack | `opsai-seed-v*` | `opsai-seed-v1.0.1` |

## Resolve order

1. Explicit `--seed-ref <ref>` on `create` / `seed`
2. Else `HAM_SEED_REF` if set
3. Else `latest` → newest GitHub tag matching `opsai-seed-v*`
4. Fetch tarball, extract `opsai-seed/` (or legacy `hermes_agent_manager/seed/`)
5. Cache under `~/.ham/seed-cache/<resolved-ref>/` for immutable refs
6. Any fetch failure → error (no packaged fallback)

Default repo: `UpGoTech/hermes-agent-manager` (`HAM_SEED_REPO`).

## CLI

| Flag / env | Effect |
|------------|--------|
| `--seed-ref <ref>` | Tag, branch, or commit |
| `HAM_SEED_REF` | Default ref when flag omitted |
| `HAM_SEED_REPO` | `owner/name` for API + tarball |

## Out of scope

- Separate seed repository
- Bundled/offline seed inside the wheel
- Auto-creating seed tags from CI
