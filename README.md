# PFUND — Implementation Dashboard & Activity Tracker

A Flask-based web application for planning, tracking and reporting on project activities, indicators and budgets for the **Pandemic Fund (PFUND)** portfolio.

The system has two integrated layers:

| Layer | Technology | Purpose |
|---|---|---|
| **Data Management** | Flask + PostgreSQL | Enter and manage activities, budgets, indicators, challenges |
| **M&E Dashboard** | Streamlit + Plotly | Interactive analytics, charts and indicator progress |

---

## Features

### Authentication & Access Control
- User registration with email confirmation (Gmail SMTP app password)
- Role-based access: `admin` and `viewer`
- Password reset via email token
- JWT-based single-sign-on between Flask and Streamlit (`jwt_utils.py`)
- Separate `app_users` table for Streamlit users (`auth_db.py`)

### Activity Management
- Create, edit and delete activities with codes, titles, descriptions and implementing entities
- Multi-year budget tracking (Year 1–3, allocated vs used)
- Sub-activities linked to parent activities
- Status tracking: Planned, In Progress, Completed, On Hold, Cancelled

### Indicators
- Define quantitative and qualitative indicators linked to activities
- Capture baseline, targets (Y1–Y3), actuals and qualitative stages
- Track submission status, portal edits and comment resolution
- Export as CSV or Excel

### Progress & Roadmap
- **Progress Tracking** — baseline vs target vs actual per year, percentage bars
- **Roadmap** — Gantt-style timeline grouped by quarter with today marker and sub-activity drill-down
- **Challenges / Follow-up** — log and track follow-up actions
- **Reports** — rich-text activity-level narrative reports

### Dashboard
- Activity counts, budget totals and execution rates
- Status breakdown table
- Budget execution by year with progress bars
- Link to M&E Streamlit dashboard

---

## Tech Stack

| Component | Library / Tool |
|---|---|
| Backend | Flask, Flask-SQLAlchemy, Flask-Migrate (Alembic) |
| Database | PostgreSQL (production), SQLite (local fallback) |
| Auth tokens | PyJWT (`jwt_utils.py`) |
| Frontend | Jinja2 templates, custom CSS design system |
| Email | Python `smtplib` via Gmail SMTP app password |
| Analytics | Streamlit + Plotly (`streamlit_app.py`) |
| Deployment | Heroku (Procfile + gunicorn) |

---

## Project Structure

```
pfund/
├── app.py                    # Flask application factory
├── activity_routes.py        # Activities, indicators, roadmap, reports, exports
├── auth_routes.py            # Login, register, password reset, user management
├── models.py                 # SQLAlchemy models (Activity, Indicator, User, …)
├── auth_db.py                # Raw SQL helpers for Streamlit app_users table
├── jwt_utils.py              # JWT sign/validate (Flask ↔ Streamlit SSO)
├── email_utils.py            # SMTP email sending
├── report_utils.py           # Report helpers
├── usage_tracking.py         # User activity logging
├── config.py                 # App configuration
├── static/
│   ├── styles.css            # Global design system (Palantir/Stripe/Notion-inspired)
│   └── css/
│       └── roadmap.css       # Roadmap page styles
├── templates/                # Jinja2 HTML templates
│   ├── base.html             # Shared layout and navigation
│   ├── index.html            # Main dashboard
│   ├── roadmap.html          # Gantt roadmap
│   ├── indicators.html       # Indicator list
│   ├── indicator_progress.html
│   ├── form.html             # Activity create/edit
│   ├── subactivity_form.html
│   ├── challenge_form.html
│   ├── report_editor.html
│   ├── report_view.html
│   ├── users.html
│   └── auth/                 # login, register, reset, confirm
├── migrations/               # Alembic migration scripts
├── streamlit_app.py          # M&E Streamlit dashboard
├── streamlit_chart.py        # Chart helpers
├── run_streamlit.bat/.sh     # Launch helpers
├── requirements.txt
├── Procfile                  # Heroku: web: gunicorn app:app
└── runtime.txt               # Python version pin
```

---

## Local Setup

### Prerequisites

- Python 3.9+
- PostgreSQL (optional — falls back to SQLite if `DATABASE_URL` is not set)

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

Create a `.flaskenv` file in the project root (Flask loads it automatically):

```env
FLASK_APP=app.py
FLASK_ENV=development

# Database — omit to fall back to SQLite (project_activities.db)
DATABASE_URL=postgresql://user:password@localhost:5432/pfund_db

# Shared between Flask and Streamlit — must match on both sides
JWT_SECRET_KEY=your-random-secret

# Flask session signing
SECRET_KEY=your-flask-secret

# Admin account — this email always gets admin role on registration
ADMIN_EMAIL=you@example.com

# Streamlit app URL (for SSO redirect link in navbar)
FLASK_AUTH_URL=http://localhost:5000

# Gmail SMTP (create an App Password at myaccount.google.com/apppasswords)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=you@gmail.com
```

### 4. Set up the database

**With PostgreSQL:**
```bash
flask db upgrade
```

**With SQLite (first run, development only):**
```bash
flask shell
>>> from models import db; db.create_all()
>>> exit()
flask db stamp head
```

### 5. Run the Flask app

```bash
flask run
```

App runs at `http://127.0.0.1:5000`.

---

## Running the M&E Dashboard (Streamlit)

The Streamlit app reads from the same database and authenticates via JWT tokens issued by Flask.

```bash
streamlit run streamlit_app.py
```

Runs at `http://localhost:8501` by default.

**Environment variables required by Streamlit** (same values as Flask):

```env
DATABASE_URL=...       # or WAREHOUSE_URL (same DB)
WAREHOUSE_URL=...
JWT_SECRET_KEY=...
FLASK_AUTH_URL=https://your-flask-app.herokuapp.com
SMTP_USER=...
SMTP_PASSWORD=...
```

The "M&E Dashboard" button in the Flask navbar redirects the logged-in user to Streamlit with a short-lived JWT token in the URL so the user is authenticated automatically.

---

## Roles & Permissions

| Action | Admin | Viewer |
|---|---|---|
| View activities, indicators, roadmap | ✓ | ✓ |
| Create / edit / delete activities | ✓ | — |
| Manage sub-activities & indicators | ✓ | — |
| Upload Excel to bulk-import activities | ✓ (super-admin only) | — |
| Manage users (promote / demote) | ✓ | — |
| View usage statistics | ✓ | — |

- The **first registered user** becomes `admin` automatically.
- Any user whose email matches `ADMIN_EMAIL` also becomes `admin`.

---

## Database Notes

### Flask models (`models.py` / `DATABASE_URL`)

Managed by SQLAlchemy + Alembic:

```bash
# After editing models.py
flask db migrate -m "describe change"
flask db upgrade
```

Tables: `users`, `activities`, `sub_activities`, `indicators`, `challenges`, `reports`, `user_activity_log`

### Streamlit users (`auth_db.py` / `WAREHOUSE_URL`)

Managed by raw SQL (`auth_db.py`). The `app_users` table is created automatically on first use via `ensure_users_table()`.

Both point to the same Heroku Postgres database in production.

---

## Deployment (Heroku)

The repo includes a `Procfile` and `runtime.txt` for Heroku.

```Procfile
web: gunicorn app:app
```

**Required Heroku config vars:**

```bash
heroku config:set FLASK_ENV=production
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

`DATABASE_URL` is set automatically by the Heroku Postgres add-on.

---

## Key Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `FLASK_APP` | Yes | `app.py` |
| `SECRET_KEY` | Yes | Flask session signing key |
| `JWT_SECRET_KEY` | Yes | Shared Flask ↔ Streamlit token secret |
| `DATABASE_URL` | Yes (prod) | PostgreSQL connection string |
| `WAREHOUSE_URL` | No | Streamlit DB override (defaults to `DATABASE_URL`) |
| `ADMIN_EMAIL` | Yes | Email that always receives admin role |
| `FLASK_AUTH_URL` | Yes | Flask base URL used by Streamlit for SSO redirect |
| `SMTP_HOST` | Yes (email) | SMTP server hostname |
| `SMTP_PORT` | Yes (email) | `587` (TLS) or `465` (SSL) |
| `SMTP_USER` | Yes (email) | SMTP login (Gmail address) |
| `SMTP_PASSWORD` | Yes (email) | Gmail App Password |
| `SMTP_FROM` | No | From address (defaults to `SMTP_USER`) |
