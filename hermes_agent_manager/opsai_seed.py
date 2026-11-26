import io
import json
import os
import re
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from hermes_agent_manager.docker_runner import CONTAINER_DATA, DockerRunner
from hermes_agent_manager.errors import InstallError

SEED_FILES = (
    "SOUL.md",
    "skills/erpnext/SKILL.md",
    "skills/erpnext/scripts/frappe.py",
)

SEED_TAG_PREFIX = "opsai-seed-v"
DEFAULT_SEED_REPO = "UpGoTech/hermes-agent-manager"
SEED_PATH_IN_REPO = "hermes_agent_manager/seed"
BUNDLED_REF = "bundled"
LATEST_REF = "latest"

_OpenUrl = Callable[[str], bytes]


def seed_root() -> Path:
    return Path(__file__).resolve().parent / "seed"


def default_seed_cache() -> Path:
    return Path.home() / ".ham" / "seed-cache"


def default_env_values() -> dict[str, str]:
    return {
        "FRAPPE_URL": "http://your-frappe-internal-host",
        "FRAPPE_URL_USER": "https://your-public-frappe-host",
        "FRAPPE_API_KEY": "replace-me",
        "FRAPPE_API_SECRET": "replace-me",
        "FM_SITE": "your-site-name",
    }


def resolve_seed_ref(explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip()
    return (os.environ.get("HAM_SEED_REF") or LATEST_REF).strip() or LATEST_REF


def resolve_seed_repo() -> str:
    return (os.environ.get("HAM_SEED_REPO") or DEFAULT_SEED_REPO).strip()


def resolve_seed_root(
    ref: str | None = None,
    *,
    cache_dir: Path | None = None,
    repo: str | None = None,
    open_url: _OpenUrl | None = None,
) -> Path:
    requested = resolve_seed_ref(ref)
    if requested == BUNDLED_REF:
        return seed_root()
    opener = open_url or _http_get
    repository = repo or resolve_seed_repo()
    cache = cache_dir or default_seed_cache()
    try:
        resolved = (
            _latest_seed_tag(repository, opener)
            if requested == LATEST_REF
            else requested
        )
        return _fetch_seed_tree(repository, resolved, cache, opener)
    except Exception as error:
        if requested != LATEST_REF and requested != BUNDLED_REF:
            raise InstallError(
                f"Could not fetch OpsAi seed ref {requested!r}: {error}"
            ) from error
        return seed_root()


def install_opsai_seed(
    docker: DockerRunner,
    container_name: str,
    env: dict[str, str] | None = None,
    seed_ref: str | None = None,
    *,
    cache_dir: Path | None = None,
    open_url: _OpenUrl | None = None,
) -> None:
    root = resolve_seed_root(
        seed_ref,
        cache_dir=cache_dir,
        open_url=open_url,
    )
    docker.exec_as_root(
        container_name,
        ["mkdir", "-p", f"{CONTAINER_DATA}/skills/erpnext/scripts"],
    )
    for relative in SEED_FILES:
        docker.copy_to_container(
            container_name,
            str(root / relative),
            f"{CONTAINER_DATA}/{relative}",
        )
    docker.exec_as_root(
        container_name,
        ["chmod", "+x", f"{CONTAINER_DATA}/skills/erpnext/scripts/frappe.py"],
    )
    docker.ensure_env(container_name, {**default_env_values(), **(env or {})})


def _fetch_seed_tree(
    repo: str,
    ref: str,
    cache_dir: Path,
    open_url: _OpenUrl,
) -> Path:
    cached = cache_dir / _cache_key(ref)
    if _is_immutable_ref(ref) and _seed_tree_complete(cached):
        return cached
    archive = open_url(_tarball_url(repo, ref))
    extracted = _extract_seed_from_tarball(archive)
    if cached.exists():
        shutil.rmtree(cached)
    cached.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(extracted, cached)
    shutil.rmtree(extracted, ignore_errors=True)
    if not _seed_tree_complete(cached):
        raise InstallError(f"Seed archive for {ref!r} is missing required files")
    return cached


def _latest_seed_tag(repo: str, open_url: _OpenUrl) -> str:
    tags: list[str] = []
    page = 1
    while page <= 5:
        payload = open_url(
            f"https://api.github.com/repos/{repo}/tags?per_page=100&page={page}"
        )
        batch = json.loads(payload.decode("utf-8"))
        if not batch:
            break
        for item in batch:
            name = item.get("name") or ""
            if name.startswith(SEED_TAG_PREFIX):
                tags.append(name)
        if len(batch) < 100:
            break
        page += 1
    if not tags:
        raise InstallError(f"No {SEED_TAG_PREFIX}* tags on {repo}")
    return max(tags, key=_seed_tag_sort_key)


def _extract_seed_from_tarball(archive: bytes) -> Path:
    staging = Path(tempfile.mkdtemp(prefix="ham-seed-"))
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            members = [
                member
                for member in tar.getmembers()
                if _safe_tar_member(member) and SEED_PATH_IN_REPO in member.name
            ]
            if not members:
                raise InstallError(f"Tarball has no {SEED_PATH_IN_REPO}/")
            tar.extractall(staging, members=members)
        matches = list(staging.glob(f"*/{SEED_PATH_IN_REPO}"))
        if not matches:
            raise InstallError(f"Could not locate {SEED_PATH_IN_REPO} in archive")
        out = Path(tempfile.mkdtemp(prefix="ham-seed-out-"))
        shutil.rmtree(out)
        shutil.copytree(matches[0], out)
        return out
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _safe_tar_member(member: tarfile.TarInfo) -> bool:
    name = member.name.replace("\\", "/")
    return not name.startswith("/") and ".." not in Path(name).parts


def _seed_tree_complete(root: Path) -> bool:
    return all((root / relative).is_file() for relative in SEED_FILES)


def _is_immutable_ref(ref: str) -> bool:
    if ref.startswith(SEED_TAG_PREFIX):
        return True
    return bool(re.fullmatch(r"[0-9a-f]{40}", ref))


def _cache_key(ref: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", ref)


def _seed_tag_sort_key(tag: str) -> tuple[int, ...]:
    body = tag[len(SEED_TAG_PREFIX) :] if tag.startswith(SEED_TAG_PREFIX) else tag
    parts: list[int] = []
    for piece in body.split("."):
        match = re.match(r"(\d+)", piece)
        parts.append(int(match.group(1)) if match else 0)
    return tuple(parts)


def _tarball_url(repo: str, ref: str) -> str:
    return f"https://codeload.github.com/{repo}/tar.gz/{ref}"


def _http_get(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "hermes-agent-manager", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise InstallError(f"HTTP {error.code} for {url}") from error
    except urllib.error.URLError as error:
        raise InstallError(f"Network error for {url}: {error.reason}") from error
