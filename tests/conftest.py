from pathlib import Path

import pytest

REPO_SEED = Path(__file__).resolve().parent.parent / "opsai-seed"


@pytest.fixture(autouse=True)
def use_repo_opsai_seed(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    if request.module.__name__.endswith("test_seed_resolve"):
        return
    monkeypatch.setattr(
        "hermes_agent_manager.opsai_seed.resolve_seed_root",
        lambda *_args, **_kwargs: REPO_SEED,
    )
