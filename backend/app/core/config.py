"""Application configuration.

This module is imported before any other part of the application, so that
backend/.env is loaded before any setting is read (previously the JWT secret
was read in core/security.py before load_dotenv() had run in main.py, so the
insecure default was used even when .env contained a secret).

The application refuses to start without a strong JWT secret: there is no
default value, because a known default would let anyone forge login tokens.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
# APP_ENV_FILE lets tests point to another file; normally backend/.env is used.
ENV_FILE = Path(os.getenv("APP_ENV_FILE", str(BACKEND_DIR / ".env")))

# Real environment variables take precedence over the file (override=False).
load_dotenv(ENV_FILE, override=False)

MIN_JWT_SECRET_LENGTH = 32
_KNOWN_WEAK_SECRETS = {
    "dev-secret-change-me",
    "a-long-random-string",
    "changeme",
    "change-me",
    "secret",
}


class ConfigError(RuntimeError):
    """Raised at start-up when a required setting is missing or unsafe."""


def load_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "").strip()
    if not secret:
        raise ConfigError(
            "JWT_SECRET_KEY is not set. Add a random value of at least "
            f"{MIN_JWT_SECRET_LENGTH} characters to backend/.env, for example the output of: "
            "python -c \"import secrets; print(secrets.token_urlsafe(48))\". "
            "The application will not start without it."
        )
    if secret.lower() in _KNOWN_WEAK_SECRETS or len(secret) < MIN_JWT_SECRET_LENGTH:
        raise ConfigError(
            f"JWT_SECRET_KEY is too weak (it must be a random value of at least "
            f"{MIN_JWT_SECRET_LENGTH} characters and not a placeholder). "
            "The application will not start with it."
        )
    return secret


JWT_SECRET_KEY = load_jwt_secret()
