import tarfile
from pathlib import Path

from hermes_agent_manager.errors import InstallError


def write_archive(directory: Path, archive: Path, profile_name: str) -> None:
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(directory, arcname=profile_name)


def extract_archive(archive: Path, data_root: Path, profile_name: str) -> None:
    with tarfile.open(archive, "r:*") as bundle:
        members = list(_safe_members(bundle, profile_name))
        if not members:
            raise InstallError(f"Archive does not contain {profile_name}.")
        bundle.extractall(data_root, members=members)


def _safe_members(bundle: tarfile.TarFile, profile_name: str) -> list[tarfile.TarInfo]:
    prefix = f"{profile_name}/"
    members = []
    for member in bundle.getmembers():
        if member.name != profile_name and not member.name.startswith(prefix):
            continue
        _reject_unsafe(member)
        members.append(member)
    return members


def _reject_unsafe(member: tarfile.TarInfo) -> None:
    parts = Path(member.name).parts
    if member.name.startswith("/") or ".." in parts or member.issym() or member.islnk():
        raise InstallError(f"Archive path is not safe: {member.name}")
