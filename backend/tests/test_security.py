"""Security tests added after the supervisor's security review.

They check the corrections made in the code:
  S-01  the JWT secret is read from backend/.env before it is used (load order)
  S-02  the backend refuses to start without a JWT secret (no default value)
  S-03  the backend refuses to start with a weak or placeholder secret
  S-04  the chat endpoint returns a generic error; the details go to the server log
  S-05  .gitignore excludes .env files, and no .env file is tracked by Git
  S-06  no Google API key is present in the frontend source code
  S-07  the module endpoints require a valid token (see also test_api_functional.py)

Run: python -m pytest tests/test_security.py -v
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
STRONG_SECRET = "s3cure-test-secret-" + "x" * 40

IMPORT_SECURITY = (
    "import sys; sys.path.insert(0, r'{backend}'); "
    "from app.core import security; print('SECRET_OK' if security.SECRET_KEY == r'{expected}' else 'SECRET_MISMATCH')"
)
IMPORT_CONFIG = "import sys; sys.path.insert(0, r'{backend}'); import app.core.config"


def _run(code, env_file, extra_env=None):
    """Run Python code in a fresh interpreter with a controlled environment."""
    env = {k: v for k, v in os.environ.items() if k not in ("JWT_SECRET_KEY", "GOOGLE_API_KEY")}
    env["APP_ENV_FILE"] = str(env_file)
    if extra_env:
        env.update(extra_env)
    return subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True,
                          cwd=str(env_file.parent), timeout=120)


def test_S01_secret_is_loaded_from_env_file_before_use(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(f"JWT_SECRET_KEY={STRONG_SECRET}\n")
    r = _run(IMPORT_SECURITY.format(backend=BACKEND_DIR, expected=STRONG_SECRET), env_file)
    assert r.returncode == 0, r.stderr
    assert "SECRET_OK" in r.stdout


def test_S02_startup_fails_without_secret(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GOOGLE_API_KEY=\n")  # no JWT_SECRET_KEY
    r = _run(IMPORT_CONFIG.format(backend=BACKEND_DIR), env_file)
    assert r.returncode != 0
    assert "ConfigError" in r.stderr and "JWT_SECRET_KEY is not set" in r.stderr


@pytest.mark.parametrize("weak", ["dev-secret-change-me", "a-long-random-string", "short-secret"])
def test_S03_startup_fails_with_weak_or_placeholder_secret(tmp_path, weak):
    env_file = tmp_path / ".env"
    env_file.write_text(f"JWT_SECRET_KEY={weak}\n")
    r = _run(IMPORT_CONFIG.format(backend=BACKEND_DIR), env_file)
    assert r.returncode != 0
    assert "too weak" in r.stderr


def test_S04_chat_error_is_generic_and_logged_on_server(app_module, alice, modules, monkeypatch, caplog):
    def boom(*a, **k):
        raise RuntimeError("internal detail: /home/kali/secret/path db=sql_app.db")

    monkeypatch.setattr(app_module.rag_service, "query_rag", boom)
    ds = modules["Data Structures"]
    with caplog.at_level("ERROR", logger="app"):
        r = alice.post("/api/chat", json={"message": "x", "context": {"title": ds["title"], "id": ds["id"], "type": "module"}})
    assert r.status_code == 500
    assert "internal detail" not in r.text and "sql_app.db" not in r.text
    assert r.json()["detail"] == "The AI tutor could not answer right now. Please try again later."
    assert any("internal detail" in (rec.exc_text or "") or "internal detail" in str(rec.exc_info)
               for rec in caplog.records), "the exception should be written to the server log"


def test_S05_gitignore_excludes_env_files():
    lines = [l.strip() for l in (REPO_DIR / ".gitignore").read_text().splitlines()]
    assert ".env" in lines
    assert "backend/.env" in lines or ".env" in lines
    if shutil.which("git") and (REPO_DIR / ".git").exists():
        tracked = subprocess.run(["git", "ls-files"], cwd=REPO_DIR, capture_output=True, text=True).stdout.split()
        offending = [f for f in tracked if os.path.basename(f) == ".env"]
        assert not offending, f".env files are still tracked by Git: {offending} (run: git rm --cached backend/.env)"


def test_S06_no_google_api_key_in_frontend_source():
    src = REPO_DIR / "frontend" / "src"
    if not src.exists():
        pytest.skip("frontend source not present")
    pattern = re.compile(r"AIza[0-9A-Za-z_\-]{20,}")
    hits = []
    for path in src.rglob("*"):
        if path.is_file() and path.suffix in {".ts", ".js", ".json", ".html", ".env"}:
            text = path.read_text(errors="ignore")
            if pattern.search(text) or "GOOGLE_API_KEY" in text:
                hits.append(str(path.relative_to(REPO_DIR)))
    assert not hits, f"possible API key in frontend files: {hits}"


def test_S07_module_endpoints_reject_anonymous_requests(client):
    for url in ["/api/modules", "/api/modules/1", "/api/modules/title/Python Programming"]:
        assert client.get(url).status_code == 401
