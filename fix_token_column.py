import os
from sqlalchemy import create_engine, text

url = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)
engine = create_engine(url, connect_args={"sslmode": "require"})
with engine.begin() as conn:
    conn.execute(text("ALTER TABLE app_users ALTER COLUMN verification_token TYPE VARCHAR(200)"))
print("Done — verification_token is now VARCHAR(200)")
