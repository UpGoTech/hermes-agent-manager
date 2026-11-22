from pathlib import Path

import pytest

from hermes_agent_manager.errors import InstallError
from hermes_agent_manager.fm_site import FmSite, list_sites, pick_site, require_sites


def test_lists_sites_with_compose(tmp_path: Path) -> None:
    site = tmp_path / "sites" / "venus.localhost"
    site.mkdir(parents=True)
    (site / "docker-compose.yml").write_text("services: {}\n")
    (tmp_path / "sites" / "empty").mkdir()

    sites = list_sites(tmp_path)

    assert [item.name for item in sites] == ["venus.localhost"]
    assert sites[0].network_name == "fm__venus_localhost__network"
    assert sites[0].frappe_container == "fm__venus_localhost__frappe"


def test_require_sites_fails_when_empty(tmp_path: Path) -> None:
    (tmp_path / "sites").mkdir()
    with pytest.raises(InstallError, match="No Frappe Manager sites"):
        require_sites(tmp_path)


def test_pick_site_uses_explicit_name(tmp_path: Path) -> None:
    _write_site(tmp_path, "venus.localhost")
    site = pick_site("venus.localhost", interactive=False, home=tmp_path)
    assert site.name == "venus.localhost"


def test_pick_site_requires_flag_without_tty(tmp_path: Path) -> None:
    _write_site(tmp_path, "venus.localhost")
    with pytest.raises(InstallError, match="Pass --site"):
        pick_site(None, interactive=False, home=tmp_path)


def test_fm_site_slug() -> None:
    assert FmSite("a.b.c").slug == "a_b_c"
    assert FmSite("a.b.c").network_name == "fm__a_b_c__network"


def _write_site(home: Path, name: str) -> None:
    path = home / "sites" / name
    path.mkdir(parents=True)
    (path / "docker-compose.yml").write_text("services: {}\n")
