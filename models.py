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
    budget_used = db.Column(db.Float, default=0)  # Budget used for Year 1 only (same as budget_used_year1)
    budget_used_year1 = db.Column(db.Float, default=0)
    budget_used_year2 = db.Column(db.Float, default=0)
    budget_used_year3 = db.Column(db.Float, default=0)
    status = db.Column(db.String, default="Planned")
    progress = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    # One-to-many: an activity can have multiple sub-activities
    sub_activities = db.relationship(
        "SubActivity",
        backref="activity",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    # One-to-one: an activity has at most one indicator
    indicator = db.relationship(
        "Indicator",
        backref="activity",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )
    # One-to-one: an activity can have one report
    report = db.relationship(
        "ActivityReport",
        backref="activity",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )


class ActivityReport(db.Model):
    """Rich-text report for an activity (one-to-one)."""
    __tablename__ = "activity_reports"

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(
        db.Integer,
        db.ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    title = db.Column(db.String(500), nullable=True)
    content_html = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    def __repr__(self):
        return f"<ActivityReport {self.id} activity_id={self.activity_id}>"


class Challenge(db.Model):
    __tablename__ = "challenges"

    id = db.Column(db.Integer, primary_key=True)
    challenge = db.Column(db.Text, nullable=False)
    action = db.Column(db.Text, nullable=False)
    responsible = db.Column(db.String, nullable=True)
    timeline = db.Column(db.String, nullable=True)
    status = db.Column(db.String, nullable=False, default="pending")


class SubActivity(db.Model):
    __tablename__ = "sub_activities"

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(
        db.Integer,
        db.ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = db.Column(db.String, nullable=False)
    responsible = db.Column(db.String, nullable=True)
    status = db.Column(db.String, nullable=False, default="pending")
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True)
    password_hash = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    # Incremented on every password change so old reset tokens become invalid immediately.
    password_version = db.Column(db.Integer, nullable=False, default=0, server_default="0")

    def generate_confirmation_token(self, expires_in: int = 3600) -> str:
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return s.dumps({"confirm": self.id}, salt="confirm-email-salt")

    @staticmethod
    def verify_confirmation_token(token: str, max_age: int = 3600):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token, salt="confirm-email-salt", max_age=max_age)
        except Exception:
            return None
        user_id = data.get("confirm")
        if not user_id:
            return None
        return db.session.get(User, user_id)

    def generate_reset_token(self, expires_in: int = 3600) -> str:
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return s.dumps({"reset": self.id, "v": self.password_version}, salt="reset-password-salt")

    @staticmethod
    def verify_reset_token(token: str, max_age: int = 3600):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token, salt="reset-password-salt", max_age=max_age)
        except Exception:
            return None
        user_id = data.get("reset")
        version = data.get("v")
        if not user_id:
            return None
        user = db.session.get(User, user_id)
        if user is None or user.password_version != version:
            return None
        return user


class UserActivity(db.Model):
    """Track user actions and usage in the system."""
    __tablename__ = "user_activities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    action = db.Column(db.String, nullable=False)  # e.g., "login", "view_activities", "create_activity", "edit_activity", "delete_activity", "download_csv"
    resource_type = db.Column(db.String, nullable=True)  # e.g., "activity", "challenge", "user"
    resource_id = db.Column(db.Integer, nullable=True)  # ID of the resource if applicable
    details = db.Column(db.Text, nullable=True)  # Additional details about the action
    ip_address = db.Column(db.String, nullable=True)  # User's IP address
    user_agent = db.Column(db.String, nullable=True)  # Browser/client info
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(), index=True)

    # Relationship to User
    user = db.relationship("User", backref="activities")

    def __repr__(self):
        return f"<UserActivity {self.id}: {self.user_id} - {self.action}>"


class Indicator(db.Model):
    """Indicators linked to activities (by activity and code)."""
    __tablename__ = "indicators"

    id = db.Column(db.Integer, primary_key=True)

    # Link to Activity (one-to-one relationship)
    activity_id = db.Column(
        db.Integer,
        db.ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Enforce one-to-one relationship
        index=True,
    )

    # Keep a copy of the activity code for reference / easier imports
    activity_code = db.Column(db.String, nullable=True, index=True)

    # Columns based on your header
    fundholder_implementing_entity = db.Column(db.String, nullable=True)
    key_project_activity = db.Column(db.Text, nullable=True)
    new_proposed_indicator = db.Column(db.Text, nullable=True)
    indicator_type = db.Column(db.String, nullable=True)
    naphs = db.Column(db.String, nullable=True)
    indicator_definition = db.Column(db.Text, nullable=True)
    data_source = db.Column(db.String, nullable=True)

    baseline_proposal_year = db.Column(db.String, nullable=True)
    target_year1 = db.Column(db.String, nullable=True)
    target_year2 = db.Column(db.String, nullable=True)
    target_year3 = db.Column(db.String, nullable=True)

    # Actual achievement values
    actual_baseline = db.Column(db.Text, nullable=True)
    actual_year1 = db.Column(db.Text, nullable=True)
    actual_year2 = db.Column(db.Text, nullable=True)
    actual_year3 = db.Column(db.Text, nullable=True)

    # Progress percentages (auto-calculated, stored for performance)
    progress_year1 = db.Column(db.Float, nullable=True)
    progress_year2 = db.Column(db.Float, nullable=True)
    progress_year3 = db.Column(db.Float, nullable=True)

    # Progress status (On Track, At Risk, Behind, Not Started)
    status_year1 = db.Column(db.String, nullable=True)
    status_year2 = db.Column(db.String, nullable=True)
    status_year3 = db.Column(db.String, nullable=True)

    # Qualitative stage fields (for qualitative indicators only)
    qualitative_stage_year1 = db.Column(db.String, nullable=True)
    qualitative_stage_year2 = db.Column(db.String, nullable=True)
    qualitative_stage_year3 = db.Column(db.String, nullable=True)

    # Last updated timestamp
    last_progress_update = db.Column(db.DateTime, nullable=True)

    submitted = db.Column(db.String, nullable=True)
    comments = db.Column(db.Text, nullable=True)
    portal_edited = db.Column(db.String, nullable=True)
    comment_addressed = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Indicator {self.id} activity_id={self.activity_id} code={self.activity_code}>"


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

