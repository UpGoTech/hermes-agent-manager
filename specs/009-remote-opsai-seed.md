# Remote OpsAi seed (same repo, separate tags)

Tracer: `ham create` / `ham seed` resolve OpsAi seed content from this GitHub repo via **seed tags**, without a HAM app release. Packaged `hermes_agent_manager/seed/` remains the offline fallback.

## Tag contract

| Kind | Pattern | Example |
|------|---------|---------|
| App release | `v*` | `v1.0.1` |
| Seed pack | `opsai-seed-v*` | `opsai-seed-v1.0.0` |

Seed tags point at any commit that contains `hermes_agent_manager/seed/` (usually `main` after content lands). App tags are unrelated; “latest seed” never selects an app tag.

## Resolve order

1. Explicit `--seed-ref <ref>` on `create` / `seed`
2. Else `HAM_SEED_REF` if set
3. Else `latest` → newest GitHub tag matching `opsai-seed-v*` (semver-ish sort)
4. Fetch `codeload.github.com/<repo>/tar.gz/<ref>`, extract `hermes_agent_manager/seed/`
5. Cache under `~/.ham/seed-cache/<resolved-ref>/` for immutable refs (seed tags / full sha)
6. If `latest` cannot be resolved or fetch fails → use packaged seed (no error)
7. If a **specific** ref was requested and fetch fails → error (do not silently use packaged)

Default repo: `UpGoTech/hermes-agent-manager` (override with `HAM_SEED_REPO`).

## CLI

| Flag / env | Effect |
|------------|--------|
| `--seed-ref <ref>` | Tag (`opsai-seed-v1.2.0`), branch, or commit |
| `HAM_SEED_REF` | Default ref when flag omitted |
| `HAM_SEED_REPO` | `owner/name` for API + tarball |

`--seed-ref bundled` forces packaged files (no network).

## Behavior vs 008

File list, container paths, memory config, and `.env` merge rules stay as in [008-opsai-seed.md](008-opsai-seed.md). Only the **source tree** changes (remote cache vs package).

## Out of scope

- Separate seed repository
- GitHub Release assets / signed manifests
- Auto-creating seed tags from CI
- Pruning the seed cache
