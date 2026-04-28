"""
auth_db.py
==========
Database functions for app_users table (Streamlit auth).
Connects to WAREHOUSE_URL / DATABASE_URL (Heroku Postgres).
"""
from __future__ import annotations

import hmac
import os
from datetime import datetime

import bcrypt
from sqlalchemy import create_engine, text


_engine = None


def _get_engine():
    global _engine
    if _engine is not None:
        return _engine
    raw_url = os.getenv("WAREHOUSE_URL") or os.getenv("DATABASE_URL", "")
    if not raw_url:
        raise EnvironmentError("Neither WAREHOUSE_URL nor DATABASE_URL is set.")
    db_url = (
        raw_url.replace("postgres://", "postgresql://", 1)
        if raw_url.startswith("postgres://")
        else raw_url
    )
    is_remote = "amazonaws.com" in db_url or "heroku" in db_url
    connect_args = {"sslmode": "require"} if is_remote else {}
    _engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
    return _engine


def ensure_users_table() -> None:
    with _get_engine().connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS app_users (
                id                 SERIAL PRIMARY KEY,
                username           VARCHAR(50)  UNIQUE NOT NULL,
                name               VARCHAR(100) NOT NULL,
                email              VARCHAR(150) UNIQUE NOT NULL,
                password_hash      VARCHAR(255) NOT NULL,
                role               VARCHAR(20)  NOT NULL DEFAULT 'analyst',
                is_active          BOOLEAN      NOT NULL DEFAULT TRUE,
                email_verified     BOOLEAN      NOT NULL DEFAULT FALSE,
                verification_token VARCHAR(200),
                token_expires_at   TIMESTAMP,
                created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login         TIMESTAMP
            )
        """))
        for stmt in [
            "ALTER TABLE app_users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE app_users ADD COLUMN IF NOT EXISTS verification_token VARCHAR(200)",
            "ALTER TABLE app_users ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMP",
        ]:
            conn.execute(text(stmt))
        conn.commit()


def db_get_user(username: str) -> dict | None:
    with _get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT * FROM app_users WHERE username=:u AND is_active=TRUE"),
            {"u": username},
        ).fetchone()
    return dict(row._mapping) if row else None


def db_get_user_by_email(email: str) -> dict | None:
    with _get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT * FROM app_users WHERE LOWER(email)=LOWER(:e) AND is_active=TRUE"),
            {"e": email},
        ).fetchone()
    return dict(row._mapping) if row else None


def db_username_exists(username: str) -> bool:
    with _get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM app_users WHERE username=:u"), {"u": username}
        ).fetchone()
    return row is not None


def db_email_exists(email: str) -> bool:
    if not email:
        return False
    with _get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM app_users WHERE LOWER(email)=LOWER(:e)"), {"e": email}
        ).fetchone()
    return row is not None


def db_register_user(username, name, email, password, role="analyst"):
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        with _get_engine().begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO app_users "
                    "(username, name, email, password_hash, role, email_verified) "
                    "VALUES (:u, :n, :e, :p, :r, FALSE)"
                ),
                {"u": username, "n": name, "e": email, "p": pw_hash, "r": role},
            )
        return True, "Account created."
    except Exception as exc:
        msg = str(exc).lower()
        if "unique" in msg or "duplicate" in msg:
            return False, "Username or email already in use."
        return False, "Registration failed. Please try again."


def db_update_last_login(username: str) -> None:
    with _get_engine().begin() as conn:
        conn.execute(
            text("UPDATE app_users SET last_login=NOW() WHERE username=:u"),
            {"u": username},
        )


def db_update_password(username: str, new_password: str) -> None:
    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    with _get_engine().begin() as conn:
        conn.execute(
            text("UPDATE app_users SET password_hash=:h WHERE username=:u"),
            {"h": pw_hash, "u": username},
        )


def db_set_token(username: str, token: str, expires_at) -> None:
    with _get_engine().begin() as conn:
        conn.execute(
            text(
                "UPDATE app_users "
                "SET verification_token=:t, token_expires_at=:e "
                "WHERE username=:u"
            ),
            {"t": token, "e": expires_at, "u": username},
        )


def db_verify_token(username: str, token: str) -> bool:
    with _get_engine().connect() as conn:
        row = conn.execute(
            text(
                "SELECT verification_token, token_expires_at "
                "FROM app_users WHERE username=:u"
            ),
            {"u": username},
        ).fetchone()
    if not row:
        return False
    stored, expires = row[0], row[1]
    if not hmac.compare_digest(stored, token):
        return False
    if expires and datetime.utcnow() > expires:
        return False
    return True


def db_mark_email_verified(username: str) -> None:
    with _get_engine().begin() as conn:
        conn.execute(
            text(
                "UPDATE app_users "
                "SET email_verified=TRUE, "
                "    verification_token=NULL, token_expires_at=NULL "
                "WHERE username=:u"
            ),
            {"u": username},
        )


def db_clear_token(username: str) -> None:
    """Invalidate the current token without changing email_verified status."""
    with _get_engine().begin() as conn:
        conn.execute(
            text(
                "UPDATE app_users "
                "SET verification_token=NULL, token_expires_at=NULL "
                "WHERE username=:u"
            ),
            {"u": username},
        )
