## PFUND Implementation Dashboard & Indicator Tracker

This repository contains a Flask‑based web application (plus an optional Streamlit dashboard) for planning, tracking and reporting on project activities and indicators for the **Pandemic Fund (PFUND)** portfolio.  
It combines:

- **Web UI** for managing activities, sub‑activities, indicators and challenges  
- **Role‑based access control** (admin vs. viewer) with email‑verified accounts  
- **Budget and progress tracking** across multiple years  
- **Indicator dashboards** (tables, charts and optional Streamlit visualizations)

---

## Features

- **User management & authentication**
  - User registration with email + password
  - Email confirmation flow (via `email_utils.py`)
  - Role‑based access (`admin` and `viewer`)
  - Login / logout and session management

- **Activity & sub‑activity management**
  - Create, edit and list project activities with codes, titles, descriptions and implementing entities
  - Track multi‑year budgets (`Year 1–3`, total, used vs allocated)
  - Define sub‑activities linked to a parent activity

- **Indicator management**
  - Define **quantitative** and **qualitative** indicators linked to activities
  - Capture indicator definitions, data sources, baseline, targets (Y1–Y3), actuals and qualitative stages
 - Mark indicators as submitted / not submitted, track portal edits and comment resolution

- **Progress tracking & dashboards**
  - **Indicator list** page with filters (search, implementing entity, type)
  - **Progress Tracking** page:
    - Baseline, target and actual values by year
    - Percentage progress bars for quantitative indicators
    - Stage/status display for qualitative indicators (Not Started / At Risk / On Track / Behind)
  - **Project dashboard** with:
    - Activity counts and budget totals
    - Status breakdown of activities
    - Budget execution by year (allocated vs used)

- **Exports & integrations**
  - Download indicators as **CSV** or **Excel**
  - Optional **Streamlit** dashboard (`streamlit_app.py`) for richer interactive charts

---

## Tech Stack

- **Backend:** [Flask](https://flask.palletsprojects.com/), [Flask‑SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/), [Flask‑Migrate/Alembic](https://flask-migrate.readthedocs.io/)
- **Database:** SQLite (default, via `project_activities.db`), can be configured for PostgreSQL (see `config.py` / `runtime.md`)
- **Frontend:** Jinja2 templates + custom CSS (`static/styles.css`), Plotly charts for visualizations
- **Optional analytics:** [Streamlit](https://streamlit.io/) + [Plotly](https://plotly.com/python/) via `streamlit_app.py`

Key entry points:

- `app.py` – main Flask application factory & server
- `activity_routes.py` – activities, indicators, progress tracking & exports
- `auth_routes.py` – authentication, registration, password reset, user management
- `models.py` – SQLAlchemy models (Activity, SubActivity, Indicator, Challenge, User, etc.)
- `templates/` – HTML templates for all pages

---

## Getting Started

### 1. Prerequisites

- **Python** 3.9+ (a `venv` folder is already present; you can use it or create your own)
- **pip** installed

### 2. Clone the repository

```bash
git clone <your-repo-url>.git
cd pfund
```

### 3. Create & activate a virtual environment (optional but recommended)

On **Windows**:

```bash
python -m venv venv
venv\Scripts\activate
```

On **macOS/Linux**:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

Configuration lives in `config.py` and environment variables. At minimum, you should set:

- `SECRET_KEY` – secret key for Flask sessions and token signing  
- `DATABASE_URL` (optional) – to use PostgreSQL in production (Heroku‑style URL, e.g. `postgresql://user:pass@host:5432/dbname`)  
- `MAIL_*` settings – if you want email confirmation and reset to work (see `email_utils.py`)  
- `ADMIN_EMAIL` – the email address that should receive admin rights on registration

You can provide these via environment variables or a `.env` file (the project includes `python-dotenv`).

Example `.env`:

```env
FLASK_ENV=development
SECRET_KEY=change-me
DATABASE_URL=sqlite:///project_activities.db
ADMIN_EMAIL=you@example.org
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=your-app-password
```

---

## Database Setup & Migrations

This project uses **Flask‑Migrate** (Alembic) with migration scripts in `migrations/`.

1. **Initialize DB (first run):**

```bash
flask db upgrade
```

> Tip: Ensure `FLASK_APP=app.py` or `FLASK_APP=app:app` is set in your environment before running `flask` commands.

2. **Create a new migration (after changing models):**

```bash
flask db migrate -m "Describe your change"
flask db upgrade
```

The default SQLite database file is `project_activities.db` in the project root.

---

## Running the Flask Web App

With your virtual environment active:

```bash
set FLASK_APP=app.py        # Windows PowerShell: $env:FLASK_APP = "app.py"
set FLASK_ENV=development   # or export FLASK_ENV=development on Linux/macOS

flask run
```

By default the app will be available at `http://127.0.0.1:5000/`.

You can also run it directly via:

```bash
python app.py
```

### Login & Roles

- The **first registered user** becomes an `admin` automatically.
- Any subsequent user whose email matches `ADMIN_EMAIL` also becomes an `admin`; others are `viewer`s.
- Admins can manage users (promote/demote), create/edit/delete activities, sub‑activities, indicators and challenges.

---

## Running the Optional Streamlit Dashboard

This project includes a separate Streamlit app for interactive indicator progress charts.

1. **Install dependencies** (if not already done):

```bash
pip install streamlit plotly
```

2. **Run Streamlit (standalone):**

```bash
streamlit run streamlit_app.py
```

By default it runs at `http://localhost:8501`.

3. **Run alongside Flask with embedded chart (optional):**

See `README_STREAMLIT.md` for step‑by‑step instructions on:

- Running Streamlit on port `8501`
- Embedding the Streamlit app into the Flask *Indicator Progress* page via `<iframe>`
- Switching between Plotly‑only and Streamlit visualization

---

## Project Structure (Overview)

```text
pfund/
├─ app.py                 # Flask app setup and entry point
├─ activity_routes.py     # Activity, indicator, challenge, progress routes & logic
├─ auth_routes.py         # Authentication & user management routes
├─ models.py              # SQLAlchemy models
├─ config​.py             # Application configuration (DB URL, secrets, etc.)
├─ static/
│   └─ styles.css         # Global styles and table/dashboard layout
├─ templates/             # Jinja2 templates (HTML)
│   ├─ index.html         # Main dashboard
│   ├─ indicators.html    # Indicator list & filters
│   ├─ indicator_progress.html  # Indicator progress table & charts
│   ├─ form.html, subactivity_form.html, challenge_form.html, ...
│   └─ auth templates (login, register, reset, etc.)
├─ streamlit_app.py       # Optional Streamlit dashboard
├─ streamlit_chart​.py    # Alternate Streamlit example
├─ requirements.txt       # Python dependencies
├─ README_STREAMLIT.md    # Streamlit‑specific documentation
├─ run_streamlit.bat/.sh  # Helper scripts to run Streamlit
├─ migrations/            # Alembic migration scripts
└─ project_activities.db  # Default SQLite database (local development)
```

---

## Deployment Notes

- A sample `Procfile` and `runtime.txt` are included for deployment to **Heroku** or similar PaaS.
- Ensure you set environment variables (especially `SECRET_KEY`, `DATABASE_URL`, and mail settings) in your hosting environment.
- For production, disable `debug` mode and use a WSGI server (e.g. `gunicorn`) as configured in `Procfile`.

Example Heroku `Procfile` (already in repo):

```Procfile
web: gunicorn app:app
```

---

## Contributing & Support

If you plan to extend this project:

- Use `flask db migrate` / `flask db upgrade` to manage schema changes.
- Keep UI changes aligned with existing design tokens in `static/styles.css`.
- Add/update tests (if you introduce them) and run them before committing.

For questions or collaboration, please open an issue or contact the project maintainer (see `ADMIN_EMAIL` in `auth_routes.py` / `config.py`).

