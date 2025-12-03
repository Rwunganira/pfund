"""Script to create challenges table if it doesn't exist."""
import os
os.environ['FLASK_APP'] = 'app.py'

from app import app
from models import db, Challenge

with app.app_context():
    try:
        # Try to create all tables (will skip if they exist)
        db.create_all()
        print("✓ Tables checked/created successfully!")
        
        # Verify challenges table exists
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        if 'challenges' in tables:
            print("✓ Challenges table exists")
            columns = [col['name'] for col in inspector.get_columns('challenges')]
            print(f"  Columns: {', '.join(columns)}")
            if 'status' in columns:
                print("✓ Status column exists")
            else:
                print("⚠ Status column missing - run: flask db upgrade")
        else:
            print("✗ Challenges table not found")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

