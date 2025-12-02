import os
from functools import wraps

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from email_utils import send_email
from models import User, db


ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "samuel.rwunganira@gmail.com")

auth_bp = Blueprint("auth", __name__)


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login", next=request.path))
        if session.get("role") != "admin":
            flash("You do not have permission to perform this action.", "error")
            return redirect(url_for("activity.index"))
        return view_func(*args, **kwargs)

    return wrapper


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user. The very first user becomes admin; others are viewers."""
    is_first_user = User.query.count() == 0

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        password_confirm = request.form.get("password_confirm") or ""

        if not username or not email or not password:
            flash("Username, email, and password are required.", "error")
        elif password != password_confirm:
            flash("Passwords do not match.", "error")
        else:
            # Decide role: first ever user OR specific admin email gets admin rights
            role = "admin" if (is_first_user or email.lower() == ADMIN_EMAIL.lower()) else "viewer"
            try:
                user = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash(password),
                    role=role,
                )
                db.session.add(user)
                db.session.commit()
                # Send confirmation email (best-effort)
                try:
                    token = user.generate_confirmation_token()
                    confirm_url = url_for("auth.confirm_email", token=token, _external=True)
                    send_email(
                        email,
                        "Confirm your Project Activity Tracker account",
                        f"Hello {username},\n\n"
                        f"Your account on the Project Activity Tracker has been created with role: {role}.\n"
                        "Please confirm your email address by clicking the link below:\n\n"
                        f"{confirm_url}\n\n"
                        "If you did not create this account, you can ignore this email.\n\n"
                        "This is an automated message.",
                    )
                except Exception:
                    flash(
                        "Account created, but confirmation email could not be sent.",
                        "info",
                    )

                flash(
                    f"User '{username}' created successfully with role '{role}'. You can now log in.",
                    "success",
                )
                return redirect(url_for("auth.login"))
            except Exception:
                flash("Username or email already exists. Choose another one.", "error")

    return render_template("register.html", is_first_user=is_first_user)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            if not user.confirmed:
                flash("Please confirm your email address before logging in. Check your inbox.", "error")
                return redirect(url_for("auth.login"))

            session["user_id"] = user.id
            session["username"] = user.username
            session["email"] = user.email
            session["role"] = user.role
            flash("Logged in successfully.", "success")
            next_url = request.args.get("next") or url_for("activity.index")
            return redirect(next_url)

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/admin/users", methods=["GET", "POST"])
@admin_required
def manage_users():
    """Simple user management screen to change roles."""
    if request.method == "POST":
        user_id = request.form.get("user_id")
        new_role = request.form.get("role")
        if user_id and new_role in ("admin", "viewer"):
            # Avoid removing your own admin rights accidentally
            if int(user_id) == session.get("user_id") and new_role != "admin":
                flash("You cannot remove your own admin rights while logged in.", "error")
            else:
                user = User.query.get(int(user_id))
                if user:
                    user.role = new_role
                    db.session.commit()
                flash("User role updated.", "success")

    users = User.query.order_by(User.username).all()
    return render_template("users.html", users=users)


@auth_bp.route("/resend-confirmation", methods=["GET", "POST"])
def resend_confirmation():
    """Ask for an email and resend a confirmation link if needed."""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        if not email:
            flash("Email is required.", "error")
            return redirect(url_for("auth.resend_confirmation"))

        user = User.query.filter_by(email=email).first()
        if user and not user.confirmed:
            try:
                token = user.generate_confirmation_token()
                confirm_url = url_for("auth.confirm_email", token=token, _external=True)
                send_email(
                    email,
                    "Resend: confirm your Project Activity Tracker account",
                    f"Hello {user.username},\n\n"
                    "Here is a new confirmation link for your Project Activity Tracker account:\n\n"
                    f"{confirm_url}\n\n"
                    "If you did not request this, you can ignore this email.\n\n"
                    "This is an automated message.",
                )
                flash(
                    "If that email is registered and not yet confirmed, a new confirmation link has been sent.",
                    "info",
                )
            except Exception:
                flash("Could not send confirmation email. Please try again later.", "error")
        else:
            # Don't reveal whether the email exists / is confirmed
            flash(
                "If that email is registered and not yet confirmed, a new confirmation link has been sent.",
                "info",
            )

        return redirect(url_for("auth.login"))

    return render_template("resend_confirmation.html")


@auth_bp.route("/confirm/<token>")
def confirm_email(token):
    """Confirm a user's email from the token link."""
    user = User.verify_confirmation_token(token)
    if not user:
        flash("The confirmation link is invalid or has expired.", "error")
        return redirect(url_for("auth.login"))

    if user.confirmed:
        flash("Account already confirmed. Please log in.", "info")
    else:
        user.confirmed = True
        db.session.commit()
        flash("Your email has been confirmed. You can now log in.", "success")

    return redirect(url_for("auth.login"))


