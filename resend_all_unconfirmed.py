"""Run with: heroku run python resend_all_unconfirmed.py --app pfund"""
from app import app

with app.app_context():
    from flask import url_for
    from models import User
    from email_utils import send_email

    unconfirmed = User.query.filter_by(confirmed=False).all()
    print(f"Found {len(unconfirmed)} unconfirmed users")

    for user in unconfirmed:
        try:
            token = user.generate_confirmation_token()
            confirm_url = url_for("auth.confirm_email", token=token, _external=True)
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
