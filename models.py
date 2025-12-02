import os

from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer

from config import DB_PATH


db = SQLAlchemy()


class Activity(db.Model):
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, nullable=True)
    initial_activity = db.Column(db.Text, nullable=True)
    proposed_activity = db.Column(db.Text, nullable=True)
    implementing_entity = db.Column(db.String, nullable=True)
    delivery_partner = db.Column(db.String, nullable=True)
    results_area = db.Column(db.String, nullable=True)
    category = db.Column(db.String, nullable=True)
    budget_year1 = db.Column(db.Float, default=0)
    budget_year2 = db.Column(db.Float, default=0)
    budget_year3 = db.Column(db.Float, default=0)
    budget_total = db.Column(db.Float, default=0)
    budget_used = db.Column(db.Float, default=0)
    status = db.Column(db.String, default="Planned")
    progress = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, nullable=True)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True)
    password_hash = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)
    confirmed = db.Column(db.Boolean, default=False)

    def generate_confirmation_token(self, expires_in: int = 3600) -> str:
        """Return a signed confirmation token for this user."""
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return s.dumps({"confirm": self.id}, salt="confirm-email-salt")

    @staticmethod
    def verify_confirmation_token(token: str, max_age: int = 3600):
        """Return the user for a valid token, or None if invalid/expired."""
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token, salt="confirm-email-salt", max_age=max_age)
        except Exception:
            return None
        user_id = data.get("confirm")
        if not user_id:
            return None
        return User.query.get(user_id)


def init_db(app) -> None:
    """Initialize SQLAlchemy and configure DB.

    - On Heroku: use DATABASE_URL (Postgres).
    - Locally: fall back to SQLite file.
    - Only auto-create tables in development.
    """
    uri = os.getenv("DATABASE_URL")
    if uri:
        # Heroku gives postgres://, SQLAlchemy expects postgresql://
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = uri
    else:
        app.config.setdefault("SQLALCHEMY_DATABASE_URI", f"sqlite:///{DB_PATH}")

    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    db.init_app(app)

    # Only create tables automatically in development
    if app.config.get("ENV") == "development":
        with app.app_context():
            db.create_all()

