import os
import sqlalchemy

url = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)
engine = sqlalchemy.create_engine(url)
with engine.begin() as conn:
    current = conn.execute(sqlalchemy.text("SELECT version_num FROM alembic_version")).fetchall()
    print("Current:", current)
    conn.execute(sqlalchemy.text("DELETE FROM alembic_version"))
    conn.execute(sqlalchemy.text("INSERT INTO alembic_version VALUES ('310e8806477a')"))
print("Stamped to 310e8806477a (true head)")
