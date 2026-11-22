import hashlib
from pathlib import Path

import pytest

import database.db as db_module

# Captured at import time, before any test patches DB_PATH.
REAL_DB = Path(db_module.DB_PATH)


def _hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def real_db_untouched():
    """Fail the run if any test modified the real expense_tracker.db."""
    before = _hash_file(REAL_DB) if REAL_DB.exists() else None
    yield
    if before is not None:
        assert _hash_file(REAL_DB) == before, "tests modified expense_tracker.db"


@pytest.fixture
def app(tmp_path, monkeypatch):
    # Patch before importing app: importing it runs init_db()/seed_db().
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    from app import app as flask_app

    db_module.init_db()
    db_module.seed_db()
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    # Overrides pytest-flask's client, which is already inside a `with` block
    # and so cannot be used as `with client:` to inspect the session.
    return app.test_client()
