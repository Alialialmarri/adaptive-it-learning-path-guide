"""Shared fixtures for the API/functional test suite.

The suite runs the real FastAPI application in-process against a throw-away
SQLite database created in a temporary directory, so it never touches the
developer's real `sql_app.db`, `chroma_db/` or `.env`.

Google Gemini is NOT called: GOOGLE_API_KEY is removed from the environment
and python-dotenv is disabled before the app is imported. Tests that need an
AI answer replace `rag_service.query_rag` with a stub, and say so in their
docstring. Retrieval quality and answer quality are measured separately by
`tests/eval/run_rag_eval.py`, which uses the real Gemini API.
"""
import os
import sys

import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEST_JWT_SECRET = "test-suite-only-secret-0123456789abcdef0123456789"


@pytest.fixture(scope="session")
def app_module(tmp_path_factory):
    workdir = tmp_path_factory.mktemp("appdata")
    previous_cwd = os.getcwd()
    os.chdir(workdir)  # database.py uses the relative path ./sql_app.db

    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ["JWT_SECRET_KEY"] = TEST_JWT_SECRET

    import dotenv

    dotenv.load_dotenv = lambda *args, **kwargs: False  # never read backend/.env

    if BACKEND_DIR not in sys.path:
        sys.path.insert(0, BACKEND_DIR)
    for name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[name]

    from app import main

    yield main
    os.chdir(previous_cwd)


@pytest.fixture(scope="session")
def client(app_module):
    from fastapi.testclient import TestClient

    with TestClient(app_module.app) as test_client:  # runs the startup seeding
        yield test_client


@pytest.fixture(scope="session")
def db_session_factory(app_module):
    return app_module.SessionLocal


class Learner:
    """Helper: a registered and logged-in test user."""

    def __init__(self, client, username):
        self.client = client
        self.username = username
        self.email = f"{username}@example.com"
        self.password = "Passw0rd-for-tests"
        r = client.post(
            "/api/auth/register",
            json={"username": username, "email": self.email, "password": self.password},
        )
        assert r.status_code == 201, r.text
        self.user_id = r.json()["id"]
        self.login()

    def login(self):
        r = self.client.post(
            "/api/auth/login", json={"username": self.username, "password": self.password}
        )
        assert r.status_code == 200, r.text
        self.token = r.json()["access_token"]
        return self.token

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def get(self, url):
        return self.client.get(url, headers=self.headers)

    def post(self, url, **kw):
        return self.client.post(url, headers=self.headers, **kw)

    def put(self, url, **kw):
        return self.client.put(url, headers=self.headers, **kw)


@pytest.fixture(scope="session")
def alice(client):
    return Learner(client, "alice_test")


@pytest.fixture(scope="session")
def bob(client):
    return Learner(client, "bob_test")


@pytest.fixture(scope="session")
def modules(alice):
    """The seeded modules, keyed by title (the module endpoints require a token)."""
    data = alice.get("/api/modules").json()
    return {m["title"]: m for m in data}
