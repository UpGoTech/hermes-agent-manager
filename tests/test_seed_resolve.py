import io
import json
import tarfile
from pathlib import Path

import pytest

from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.opsai_seed import (
    SEED_FILES,
    SEED_PATH_IN_REPO,
    resolve_seed_ref,
    resolve_seed_root,
    seed_root,
)


def test_resolve_seed_ref_prefers_explicit_then_env(monkeypatch) -> None:
    monkeypatch.setenv("HAM_SEED_REF", "opsai-seed-v1.0.0")
    assert resolve_seed_ref("opsai-seed-v9.9.9") == "opsai-seed-v9.9.9"
    assert resolve_seed_ref(None) == "opsai-seed-v1.0.0"
    monkeypatch.setenv("HAM_SEED_REF", "")
    assert resolve_seed_ref(None) == "latest"


def test_bundled_ref_skips_network(tmp_path: Path) -> None:
    def boom(_url: str) -> bytes:
        raise AssertionError("network should not be used")

    root = resolve_seed_root("bundled", cache_dir=tmp_path, open_url=boom)
    assert root == seed_root()


def test_latest_falls_back_to_bundled_when_no_tags(tmp_path: Path) -> None:
    def open_url(url: str) -> bytes:
        if "api.github.com" in url:
            return b"[]"
        raise AssertionError(url)

    root = resolve_seed_root("latest", cache_dir=tmp_path, open_url=open_url)
    assert root == seed_root()


def test_latest_fetches_newest_seed_tag(tmp_path: Path) -> None:
    archive = _seed_tarball(tmp_path, soul="# from remote\n")

    def open_url(url: str) -> bytes:
        if "api.github.com" in url and "page=1" in url:
            return json.dumps(
                [
                    {"name": "v1.0.1"},
                    {"name": "opsai-seed-v1.0.0"},
                    {"name": "opsai-seed-v1.2.0"},
                    {"name": "opsai-seed-v1.10.0"},
                ]
            ).encode()
        if "api.github.com" in url:
            return b"[]"
        if "opsai-seed-v1.10.0" in url:
            return archive
        raise AssertionError(url)

    root = resolve_seed_root("latest", cache_dir=tmp_path / "cache", open_url=open_url)
    assert (root / "SOUL.md").read_text() == "# from remote\n"
    assert root == tmp_path / "cache" / "opsai-seed-v1.10.0"


def test_cached_immutable_ref_skips_download(tmp_path: Path) -> None:
    cache = tmp_path / "cache" / "opsai-seed-v1.0.0"
    _copy_seed_tree(cache, soul="# cached\n")
    calls: list[str] = []

    def open_url(url: str) -> bytes:
        calls.append(url)
        raise AssertionError("should use cache")

    root = resolve_seed_root(
        "opsai-seed-v1.0.0",
        cache_dir=tmp_path / "cache",
        open_url=open_url,
    )
    assert root == cache
    assert calls == []
    assert (root / "SOUL.md").read_text() == "# cached\n"


def test_explicit_ref_errors_when_fetch_fails(tmp_path: Path) -> None:
    def open_url(_url: str) -> bytes:
        raise InstallError("boom")

    with pytest.raises(InstallError, match="Could not fetch OpsAi seed ref"):
        resolve_seed_root(
            "opsai-seed-v9.9.9",
            cache_dir=tmp_path,
            open_url=open_url,
        )


def test_ignores_app_tags_when_picking_latest(tmp_path: Path) -> None:
    archive = _seed_tarball(tmp_path, soul="# seed\n")

    def open_url(url: str) -> bytes:
        if "api.github.com" in url and "page=1" in url:
            return json.dumps(
                [{"name": "v9.9.9"}, {"name": "opsai-seed-v0.1.0"}]
            ).encode()
        if "api.github.com" in url:
            return b"[]"
        if "opsai-seed-v0.1.0" in url:
            return archive
        raise AssertionError(url)

    root = resolve_seed_root("latest", cache_dir=tmp_path / "cache", open_url=open_url)
    assert (root / "SOUL.md").read_text() == "# seed\n"


def _copy_seed_tree(destination: Path, soul: str) -> None:
    packaged = seed_root()
    for relative in SEED_FILES:
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative == "SOUL.md":
            path.write_text(soul)
        else:
            path.write_bytes((packaged / relative).read_bytes())


def _seed_tarball(tmp_path: Path, soul: str) -> bytes:
    tree = tmp_path / "tree" / "hermes-agent-manager-abc" / SEED_PATH_IN_REPO
    _copy_seed_tree(tree, soul=soul)
    buffer = io.BytesIO()
    root_name = "hermes-agent-manager-abc"
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.add(tree, arcname=f"{root_name}/{SEED_PATH_IN_REPO}")
    return buffer.getvalue()
