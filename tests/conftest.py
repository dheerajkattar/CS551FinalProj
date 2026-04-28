import os
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def add_repo_to_pythonpath():
    """Allow test modules to import app packages by path."""
    root_str = str(REPO_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    yield


@pytest.fixture
def clean_env(monkeypatch):
    """Provide a simple environment isolation helper."""
    for key in ("DATABASE_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    yield
