from flask import Flask, session
from flask_migrate import Migrate

from activity_routes import activity_bp
from auth_routes import auth_bp
from config import SECRET_KEY
from models import db, init_db


app = Flask(__name__)
app.secret_key = SECRET_KEY

# Initialise SQLAlchemy and create tables (first run) or connect to existing DB
init_db(app)

# Set up Alembic/Flask-Migrate for schema migrations
migrate = Migrate(app, db)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(activity_bp)


@app.context_processor
def inject_current_user():
    """Expose simple current_user info to all templates."""
    return {
        "current_user": {
            "id": session.get("user_id"),
            "username": session.get("username"),
            "email": session.get("email"),
            "role": session.get("role"),
        }
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
    app.run(debug=True)




