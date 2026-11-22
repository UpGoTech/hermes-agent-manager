from pathlib import Path

from hermes_agent_manager.storage import runtime_mount


def test_runtime_mount_uses_volume_when_required(monkeypatch) -> None:
    monkeypatch.setattr("hermes_agent_manager.storage.needs_named_volume", lambda: True)
    assert runtime_mount("ham-venus-stm", Path("/tmp/data")) == "ham-venus-stm"


def test_runtime_mount_uses_host_path_when_safe(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("hermes_agent_manager.storage.needs_named_volume", lambda: False)
    path = tmp_path / "venus.localhost" / "stm"
    path.mkdir(parents=True)
    assert runtime_mount("ham-venus-stm", path) == str(path.resolve())
