from pathlib import Path


def build_context() -> Path:
    return Path(__file__).resolve().parent
