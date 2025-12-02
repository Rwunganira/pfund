import os
import smtplib
from email.message import EmailMessage


def _build_message(from_email: str, to_email: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(body)
    return msg


def send_email(to_email: str, subject: str, body: str) -> None:
    """Send an email using SMTP configuration from environment variables.

    Supports TLS on port 587 and SSL on port 465 depending on SMTP_PORT.
    Logs clear errors to the console when something goes wrong.
    """
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM") or user

    if not (host and port and user and password and from_email):
        print("SMTP CONFIG MISSING:", host, port, user, bool(password), from_email)
        return

    msg = _build_message(from_email, to_email, subject, body)

    try:
        # Use SSL for port 465, TLS for others (587 by default)
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(msg)
        print("SMTP OK: message sent")
    except Exception as exc:
        print("SMTP ERROR:", repr(exc))
