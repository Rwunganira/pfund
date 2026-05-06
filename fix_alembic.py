import os
import sqlalchemy

url = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)
engine = sqlalchemy.create_engine(url)
with engine.begin() as conn:
    result = conn.execute(sqlalchemy.text("SELECT version_num FROM alembic_version"))
    current = result.fetchall()
    print("Current versions:", current)
    conn.execute(sqlalchemy.text("DELETE FROM alembic_version"))
    conn.execute(sqlalchemy.text("INSERT INTO alembic_version VALUES ('eb786a4b61a0')"))
print("Stamped to eb786a4b61a0")
