"""Run with: heroku run python resend_all_unconfirmed.py --app pfund"""
import os
from app import app

BASE_URL = os.getenv("FLASK_AUTH_URL", "https://pfund-2f829dd9fade.herokuapp.com")

with app.app_context():
    from models import User
    from email_utils import send_email

    unconfirmed = User.query.filter_by(confirmed=False).all()
    print(f"Found {len(unconfirmed)} unconfirmed users")

    for user in unconfirmed:
        try:
            token = user.generate_confirmation_token()
            confirm_url = f"{BASE_URL}/confirm/{token}"
            send_email(
                user.email,
                "Confirm your Project Activity Tracker account",
                f"Hello {user.username},\n\n"
                f"Please confirm your email address by clicking the link below:\n\n"
                f"{confirm_url}\n\n"
                "This link expires in 1 hour.\n\n"
                "If you did not create this account, ignore this email.",
            )
            print(f"OK  {user.email}")
        except Exception as exc:
            print(f"ERR {user.email}: {exc}")
