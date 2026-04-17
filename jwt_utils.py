"""
jwt_utils.py
============
JWT helpers: Flask signs, Streamlit validates.
Requires JWT_SECRET_KEY env var (same value in both apps).
"""

import os
from datetime import datetime, timedelta, timezone

import jwt  # PyJWT


_SECRET = None


def _secret() -> str:
    global _SECRET
    if _SECRET is None:
        _SECRET = os.getenv("JWT_SECRET_KEY", "")
        if not _SECRET:
            raise EnvironmentError("JWT_SECRET_KEY is not set.")
    return _SECRET


def create_dashboard_token(
    username: str,
    name: str,
    role: str,
    email: str,
    expires_minutes: int = 60,
) -> str:
    payload = {
        "sub":   username,
        "name":  name,
        "role":  role,
        "email": email,
        "iat":   datetime.now(timezone.utc),
        "exp":   datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, _secret(), algorithm="HS256")


def validate_dashboard_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None
