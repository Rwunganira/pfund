from flask import Flask, session
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import os

from activity_routes import activity_bp
from auth_routes import auth_bp
from flask_auth import auth_bp as pfund_auth_bp
from auth_db import ensure_users_table
from config import SECRET_KEY
from extensions import limiter
from models import db, init_db


app = Flask(__name__)
app.secret_key = os.getenv("JWT_SECRET_KEY", SECRET_KEY)

csrf = CSRFProtect(app)
limiter.init_app(app)

# Initialise SQLAlchemy and create tables (first run) or connect to existing DB
init_db(app)

# Set up Alembic/Flask-Migrate for schema migrations
migrate = Migrate(app, db)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(activity_bp)
app.register_blueprint(pfund_auth_bp)

# Bootstrap app_users table for Streamlit auth (only when a DB URL is configured)
if os.getenv("WAREHOUSE_URL") or os.getenv("DATABASE_URL"):
    try:
        ensure_users_table()
    except Exception as _e:
        print(f"Warning: could not ensure app_users table: {_e}")



@app.context_processor
def inject_current_user():
    """Expose simple current_user info to all templates."""
    _admin_email = os.getenv("ADMIN_EMAIL", "samuel.rwunganira@gmail.com")
    user_email = session.get("email") or ""
    return {
        "current_user": {
            "id": session.get("user_id"),
            "username": session.get("username"),
            "email": user_email,
            "role": session.get("role"),
        },
        "is_super_admin": bool(user_email and user_email.lower() == _admin_email.lower()),
    }


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors and log debug info."""
    import traceback
    error_msg = str(error)
    tb = traceback.format_exc()
    print(f"500 Error: {error_msg}")
    print(tb)
    # On Heroku, this will appear in logs
    # Return a simple error page
    return "<h1>Internal Server Error</h1><p>An error occurred. Please check the logs.</p>", 500


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")




