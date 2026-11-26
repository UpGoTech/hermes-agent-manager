import pytest


@pytest.fixture(autouse=True)
def use_bundled_opsai_seed(monkeypatch) -> None:
    monkeypatch.setenv("HAM_SEED_REF", "bundled")
