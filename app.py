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


if __name__ == "__main__":
    app.run(debug=True)




