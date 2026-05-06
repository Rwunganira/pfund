# PFUND — Implementation Dashboard & Activity Tracker

A Flask web application for planning, tracking and reporting on activities, indicators and budgets for the **Pandemic Fund (PFUND)** portfolio.

---

## Architecture

| Layer | Technology | Purpose |
|---|---|---|
| **Data Management** | Flask + SQLAlchemy | Enter and manage activities, budgets, indicators, challenges |
| **M&E Dashboard** | Streamlit + Plotly | Indicator progress charts and analytics |

The two layers run as separate processes and communicate via short-lived JWT tokens (SSO). Clicking "M&E Dashboard" in the Flask navbar issues a JWT and redirects the user to the Streamlit app already authenticated.

### Local vs Production

| Environment | Flask DB | Streamlit app | Streamlit DB |
|---|---|---|---|
| **Local** | SQLite (`project_activities.db`) | `streamlit_app.py` at port 8501 | Same SQLite via Flask models |
| **Production** | Heroku Postgres | `pfund_streamlit_2` on Streamlit Cloud | Heroku Postgres (mart tables via ETL) |

---

## Features

### Activity Management
- Create, edit and delete activities with codes, titles, implementing entities and categories
- Multi-year budget tracking (Year 1–3, allocated vs used) with execution rates
- Sub-activities linked to parent activities
- Status tracking: Planned, In Progress, Completed, On Hold, Cancelled

### Indicators
- Quantitative and qualitative indicators linked to activities
- Baseline, targets (Y1–Y3), actuals, qualitative stages and progress %
- Submission status, portal edit tracking and comment resolution
- Export to CSV or Excel

### Progress & Roadmap
- Per-year indicator progress: On Track / At Risk / Behind / Not Started
- Gantt-style roadmap grouped by quarter with sub-activity drill-down
- Challenge and follow-up action log
- Rich-text activity narrative reports

### Authentication & Access Control
- Registration with email confirmation (Gmail SMTP App Password)
- Password reset via time-expiring email token
- Role-based access: `admin` and `viewer`
- JWT-based SSO between Flask and Streamlit

---

## Tech Stack

| Component | Library |
|---|---|
| Backend | Flask 3, Flask-SQLAlchemy, Flask-Migrate (Alembic) |
| Database | PostgreSQL (production), SQLite (local) |
| Auth | PyJWT, bcrypt, Flask-WTF (CSRF) |
| Frontend | Jinja2 templates, custom CSS |
| Email | `smtplib` via Gmail SMTP App Password |
| Rate limiting | Flask-Limiter |
| Analytics | Streamlit 1.12, Plotly 5 |
| Deployment | Heroku (gunicorn) |

---

## Project Structure

```
pfund/
├── app.py                      # Flask app factory
├── activity_routes.py          # Activities, indicators, roadmap, reports, exports
├── auth_routes.py              # Login, register, password reset, user management
├── models.py                   # SQLAlchemy models (Activity, Indicator, User …)
├── auth_db.py                  # Raw SQL helpers for app_users (Streamlit auth)
├── jwt_utils.py                # JWT sign / validate (Flask ↔ Streamlit SSO)
├── email_utils.py              # SMTP email sending
├── report_utils.py             # Report helpers
├── usage_tracking.py           # User activity logging
├── config.py                   # App configuration constants
├── extensions.py               # Shared Flask extensions (limiter)
├── flask_auth/                 # Auth blueprint (registration, login, JWT redirect)
│   ├── routes.py
│   └── email_utils.py
├── static/
│   ├── styles.css              # Global design system
│   └── css/roadmap.css
├── templates/                  # Jinja2 templates
│   ├── base.html               # Shared layout and navigation
│   ├── index.html              # Main dashboard
│   ├── indicator_progress.html
│   ├── roadmap.html
│   ├── indicators.html
│   ├── form.html               # Activity create/edit
│   └── …
├── migrations/                 # Alembic migration scripts
├── streamlit_app.py            # Local M&E Streamlit dashboard
├── streamlit_chart.py          # Alternative chart entry point
├── run_streamlit.bat           # Windows Streamlit launcher
├── run_streamlit.sh            # macOS/Linux Streamlit launcher
├── .flaskenv                   # Local environment variables (not committed with secrets)
├── requirements.txt
├── Procfile                    # Heroku: gunicorn app:app
└── runtime.txt                 # Python version pin
```

---

## Local Setup

### Prerequisites
- Python 3.9+
- No PostgreSQL needed — falls back to SQLite automatically

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd pfund
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

`.flaskenv` is loaded automatically by Flask. Create or edit it in the project root:

```env
FLASK_APP=app.py

# Database — leave commented out to use local SQLite (project_activities.db)
# DATABASE_URL=postgresql://user:password@localhost:5432/pfund_db

# Shared JWT secret — must match Streamlit app
JWT_SECRET_KEY=your-random-secret-here

# Flask session signing key
SECRET_KEY=your-flask-secret-here

# Email that always receives admin role on registration
ADMIN_EMAIL=you@example.com

# Base URL of this Flask app (used by Streamlit for SSO back-link)
FLASK_AUTH_URL=http://localhost:5000

# Gmail SMTP — create an App Password at myaccount.google.com/apppasswords
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=you@gmail.com
```

### 4. Set up the database

SQLite is created automatically the first time you run the app via `db.create_all()` (triggered when `FLASK_ENV=development`). To use Alembic migrations instead:

```bash
flask db upgrade
```

### 5. Run Flask

```bash
flask run
```

App available at `http://127.0.0.1:5000`.

---

## Running the M&E Dashboard (Streamlit)

The local Streamlit app reads from the same SQLite database as Flask. Run it in a **separate terminal** while Flask is running:

```bash
# Windows (with venv active)
venv\Scripts\streamlit run streamlit_app.py --server.port 8501

# or
run_streamlit.bat
```

The "M&E Dashboard" button in the Flask navbar redirects to `http://localhost:8501` with a JWT token so the user is authenticated automatically.

> **Note:** Streamlit 1.39.0 requires Python 3.10+. This project uses Python 3.9 so it installs Streamlit 1.12.0. The `requirements.txt` reflects this.

---

## Roles & Permissions

| Action | Admin | Viewer |
|---|---|---|
| View activities, indicators, roadmap | ✓ | ✓ |
| Create / edit / delete activities | ✓ | — |
| Manage indicators and sub-activities | ✓ | — |
| Bulk import via Excel | ✓ (super-admin) | — |
| Manage users (promote / demote / deactivate) | ✓ | — |
| View usage statistics | ✓ | — |

- The email matching `ADMIN_EMAIL` always receives the `admin` role on registration.

---

## Database & Migrations

Flask models are managed by SQLAlchemy + Alembic:

```bash
# After editing models.py — generate and apply a migration
flask db migrate -m "describe the change"
flask db upgrade
```

Tables: `users`, `activities`, `sub_activities`, `indicators`, `challenges`, `reports`, `user_activity_log`

The `app_users` table (Streamlit authentication) is managed separately by raw SQL in `auth_db.py` and is created automatically on startup when a database URL is configured.

---

## Deployment (Heroku)

```
web: gunicorn app:app
release: flask db upgrade
```

**Required Heroku config vars:**

```bash
heroku config:set SECRET_KEY=...
heroku config:set JWT_SECRET_KEY=...
heroku config:set ADMIN_EMAIL=...
heroku config:set FLASK_AUTH_URL=https://your-app.herokuapp.com
heroku config:set SMTP_HOST=smtp.gmail.com
heroku config:set SMTP_PORT=587
heroku config:set SMTP_USER=...
heroku config:set SMTP_PASSWORD=...
heroku config:set SMTP_FROM=...
```

`DATABASE_URL` is set automatically by the Heroku Postgres add-on. The M&E Dashboard in production is served by a separate `pfund_streamlit_2` app on Streamlit Cloud.

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `FLASK_APP` | Yes | `app.py` |
| `SECRET_KEY` | Yes | Flask session signing key |
| `JWT_SECRET_KEY` | Yes | Shared Flask ↔ Streamlit token secret |
| `DATABASE_URL` | Prod only | PostgreSQL connection string (Heroku sets this automatically) |
| `WAREHOUSE_URL` | No | Streamlit DB override; falls back to `DATABASE_URL` |
| `ADMIN_EMAIL` | Yes | Email that always receives admin role |
| `FLASK_AUTH_URL` | Yes | Flask base URL (used by Streamlit for login redirect) |
| `STREAMLIT_URL` | No | Streamlit base URL; defaults to `http://localhost:8501` |
| `SMTP_HOST` | Email only | SMTP server (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | Email only | `587` (TLS) |
| `SMTP_USER` | Email only | Gmail address |
| `SMTP_PASSWORD` | Email only | Gmail App Password |
| `SMTP_FROM` | No | From address; defaults to `SMTP_USER` |
