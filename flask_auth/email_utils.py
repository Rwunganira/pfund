"""
flask_auth/email_utils.py
=========================
OTP / link email sender for the Streamlit auth flow.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_otp_email(to_email: str, name: str, otp: str, purpose: str = "verify") -> bool:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    from_email = os.getenv("FROM_EMAIL", smtp_user)

    if not smtp_user or not smtp_pass:
        return False

    is_link = otp.startswith("http")

    subjects = {
        "verify":      "Pandemic Fund M&E — Verify your email",
        "verify_link": "Pandemic Fund M&E — Confirm your email",
        "reset":       "Pandemic Fund M&E — Password reset code",
        "reset_link":  "Pandemic Fund M&E — Reset your password",
    }
    subject = subjects.get(purpose, "Pandemic Fund M&E — Action required")

    if is_link:
        action_label = "Reset Password" if "reset" in purpose else "Verify Email"
        body = f"""
        <p>Click the button below. The link expires in <strong>1 hour</strong>.</p>
        <div style="text-align:center;margin:32px 0">
          <a href="{otp}"
             style="background:#2c3e50;color:#fff;padding:14px 28px;
                    border-radius:6px;text-decoration:none;font-size:1rem">
            {action_label}
          </a>
        </div>
        <p style="color:#7f8c8d;font-size:0.85em">
          Or copy this link: <a href="{otp}">{otp}</a>
        </p>"""
    else:
        intro = ("Thank you for registering. Use the code below to verify your email."
                 if "verify" in purpose
                 else "We received a password reset request. Use the code below.")
        body = f"""
        <p>{intro}</p>
        <div style="background:#f0f4f8;border-radius:8px;padding:24px;
                    text-align:center;margin:24px 0">
          <span style="font-size:36px;font-weight:bold;
                       letter-spacing:8px;color:#2c3e50">{otp}</span>
        </div>
        <p style="color:#7f8c8d;font-size:0.85em">
          Expires in <strong>15 minutes</strong>.
        </p>"""

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto">
      <h2 style="color:#2c3e50">Pandemic Fund M&amp;E</h2>
      <p>Hello <strong>{name}</strong>,</p>
      {body}
      <p style="color:#7f8c8d;font-size:0.85em">
        If you did not request this, you can safely ignore this email.
      </p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_email
    msg["To"]      = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to_email, msg.as_string())
        return True
    except Exception:
        return False
