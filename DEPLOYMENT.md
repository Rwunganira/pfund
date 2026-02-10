# Heroku Deployment Guide

This guide will help you deploy your PFUND application to Heroku.

## Prerequisites

1. **Heroku Account**: Sign up at [heroku.com](https://www.heroku.com)
2. **Heroku CLI**: Install from [devcenter.heroku.com/articles/heroku-cli](https://devcenter.heroku.com/articles/heroku-cli)
3. **Git**: Ensure Git is installed and your project is a Git repository

## Step 1: Install Heroku CLI

Download and install the Heroku CLI for your operating system from the official website.

## Step 2: Login to Heroku

```bash
heroku login
```

This will open a browser window for authentication.

## Step 3: Create a Heroku App

```bash
# Navigate to your project directory
cd C:\Users\HP\practice\pfund

# Create a new Heroku app (replace 'your-app-name' with your desired name)
heroku create your-app-name

# Or let Heroku generate a random name
heroku create
```

## Step 4: Add PostgreSQL Database

Heroku provides a free PostgreSQL database addon:

```bash
heroku addons:create heroku-postgresql:mini
```

This will automatically set the `DATABASE_URL` environment variable.

## Step 5: Set Environment Variables

Set your secret key and admin email:

```bash
# Generate a secure secret key (you can use Python: import secrets; secrets.token_hex(32))
heroku config:set SECRET_KEY="your-secret-key-here"

# Set admin email
heroku config:set ADMIN_EMAIL="samuel.rwunganira@gmail.com"
```

## Step 6: Configure Email Settings (Optional)

If you're using email functionality, set up SMTP settings:

```bash
heroku config:set MAIL_SERVER="smtp.gmail.com"
heroku config:set MAIL_PORT=587
heroku config:set MAIL_USE_TLS=True
heroku config:set MAIL_USERNAME="your-email@gmail.com"
heroku config:set MAIL_PASSWORD="your-app-password"
```

## Step 7: Initialize Git Repository (if not already done)

```bash
git init
git add .
git commit -m "Initial commit for Heroku deployment"
```

## Step 8: Deploy to Heroku

```bash
# Add Heroku remote (if not already added)
heroku git:remote -a your-app-name

# Deploy
git push heroku main
# Or if your default branch is 'master':
git push heroku master
```

## Step 9: Run Database Migrations

After deployment, run the database migrations:

```bash
heroku run flask db upgrade
```

## Step 10: Open Your App

```bash
heroku open
```

## Post-Deployment Checklist

- [ ] Verify the app is running
- [ ] Check that database migrations completed successfully
- [ ] Test user registration and login
- [ ] Verify email functionality (if configured)
- [ ] Test creating/editing activities
- [ ] Check usage statistics page

## Useful Heroku Commands

```bash
# View logs
heroku logs --tail

# Run a one-off command
heroku run python

# View environment variables
heroku config

# Scale dynos (if needed)
heroku ps:scale web=1

# Restart the app
heroku restart

# Open a database console
heroku pg:psql
```

## Check if Heroku database was deleted

Run these from your machine (with Heroku CLI installed and logged in):

```bash
# 1. Confirm you're on the right app
heroku apps:info

# 2. See if DATABASE_URL is set (if empty, the addon may be gone)
heroku config:get DATABASE_URL

# 3. List Postgres addons and status
heroku addons

# 4. Postgres addon info (plan, state, created_at)
heroku pg:info

# 5. Connect to DB and list tables (confirms DB exists and is reachable)
heroku pg:psql -c "\dt"
```

**How to interpret:**
- **`DATABASE_URL` is empty** → No Postgres addon; database was removed or never added. Re-add with: `heroku addons:create heroku-postgresql:mini` then `heroku run flask db upgrade`.
- **`heroku addons`** shows no `heroku-postgresql` → Addon was destroyed. Re-add as above.
- **`heroku pg:info`** shows "Available" and a plan → Addon exists; if the app still errors, check migrations and logs.
- **`heroku pg:psql -c "\dt"`** lists tables → Database is there; if data is missing, only app data was deleted (e.g. via "Delete all activities"), not the DB itself.

This app does **not** run any code that destroys the Heroku Postgres addon; it only deletes rows/tables inside the app (activities, challenges, etc.).

## Troubleshooting

### Database Issues
- Ensure `DATABASE_URL` is set: `heroku config:get DATABASE_URL`
- Run migrations: `heroku run flask db upgrade`
- Check database connection: `heroku pg:info`

### Application Errors
- Check logs: `heroku logs --tail`
- Verify all environment variables are set
- Ensure `requirements.txt` includes all dependencies

### Migration Issues
- Check migration status: `heroku run flask db current`
- View migration history: `heroku run flask db history`
- If needed, manually run migrations: `heroku run flask db upgrade`

## Notes

- The `Procfile` is already configured to use Gunicorn
- `requirements.txt` includes all necessary dependencies
- The app automatically uses `DATABASE_URL` on Heroku (PostgreSQL)
- Local development uses SQLite, production uses PostgreSQL

## Updating the App

After making changes:

```bash
git add .
git commit -m "Description of changes"
git push heroku main
heroku run flask db upgrade  # If you added new migrations
```

