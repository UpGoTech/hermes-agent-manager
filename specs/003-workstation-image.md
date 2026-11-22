# Workstation image (beta)

Tracer bullet: `ham create` runs a FM-style fat image so `ham shell` has real CLI tools.

## Behavior

1. Ship a Dockerfile under `hermes_agent_manager/image/` that starts `FROM nousresearch/hermes-agent:latest`.
2. Install interactive packages: `vim`, `nano`, `less`, `tree`, `jq`, `sudo`, `wget`, `bash-completion`, `net-tools`, `iproute2`, `file`, `unzip`, `locales`.
3. Passwordless sudo for every user (local beta workstation; same idea as FM's `frappe` sudo).
4. System-wide bash config at `/etc/bash.bashrc.d/ham.bashrc` (aliases, history, colored prompt). Shell stays bash — current FM also left zsh.
5. Tag the built image `ham/hermes-agent:latest`.
6. `ham create` builds that tag when it is missing (Docker pulls the Hermes base during build). Existing agents keep working; new creates use the ham image.
7. `ham build-image` force-rebuilds with `--pull` so base updates are easy to test.
8. `ham shell` / profile create `docker exec` as `HERMES_UID:HERMES_GID` so the CLI matches the gateway user (root shells leave root-owned files and trip `gateway.sock` checks).

```mermaid
flowchart LR
  create["ham create"] --> ensure["image present?"]
  ensure -->|no| build["docker build ham/hermes-agent"]
  build --> base["FROM nousresearch/hermes-agent"]
  ensure -->|yes| run["container HA-name"]
  build --> run
  shell["ham shell"] --> exec["docker exec bash"]
  exec --> tools["vim jq tree sudo ..."]
```

## Layout

- `hermes_agent_manager/image/Dockerfile`
- `hermes_agent_manager/image/bashrc`
- `hermes_agent_manager/image/paths.py` — resolve packaged build context
- `docker_runner.py` — `image_exists`, `build_image`; default `IMAGE` becomes `ham/hermes-agent:latest`
- `installer.py` — ensure/build instead of bare `docker pull` of the official tag
- `cli.py` — `build-image` command

## Tests

- Create builds when the ham image is absent, skips build when present, then runs the gateway with `ham/hermes-agent:latest`
- `build-image` runs `docker build --pull -t ham/hermes-agent:latest <context>`
- Shell and profile create pass `--user` from the container's `HERMES_UID` / `HERMES_GID`

## Out of scope

- Publishing to a registry
- zsh / oh-my-zsh
- Migrating existing `HA-*` containers that still use the official image
