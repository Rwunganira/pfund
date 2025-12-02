from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "project_activities.db"

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-key")


