"""
Script to check if the indicators table schema matches the model definition.
Run this in both dev and production to compare schemas.

Usage:
  python check_indicator_schema.py
"""
import os
from flask import Flask
from models import db, Indicator
from sqlalchemy import inspect

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///project_activities.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    inspector = inspect(db.engine)
    
    # Get actual table columns from database
    if inspector.has_table('indicators'):
        actual_columns = {col['name']: str(col['type']) for col in inspector.get_columns('indicators')}
        actual_indexes = [idx['name'] for idx in inspector.get_indexes('indicators')]
        
        print("=" * 60)
        print("INDICATORS TABLE SCHEMA CHECK")
        print("=" * 60)
        print(f"\nDatabase: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1] if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite'}")
        print(f"\nTotal columns: {len(actual_columns)}")
        print("\nColumns in database:")
        for col_name, col_type in sorted(actual_columns.items()):
            print(f"  - {col_name}: {col_type}")
        
        print(f"\nIndexes: {', '.join(actual_indexes) if actual_indexes else 'None'}")
        
        # Expected columns from model
        expected_columns = {
            'id', 'activity_id', 'activity_code',
            'fundholder_implementing_entity', 'key_project_activity', 'new_proposed_indicator',
            'indicator_type', 'naphs', 'indicator_definition', 'data_source',
            'baseline_proposal_year', 'target_year1', 'target_year2', 'target_year3',
            'actual_baseline', 'actual_year1', 'actual_year2', 'actual_year3',
            'progress_year1', 'progress_year2', 'progress_year3',
            'status_year1', 'status_year2', 'status_year3',
            'qualitative_stage_year1', 'qualitative_stage_year2', 'qualitative_stage_year3',
            'last_progress_update',
            'submitted', 'comments', 'portal_edited', 'comment_addressed'
        }
        
        actual_col_names = set(actual_columns.keys())
        missing = expected_columns - actual_col_names
        extra = actual_col_names - expected_columns
        
        print("\n" + "=" * 60)
        print("SCHEMA VALIDATION")
        print("=" * 60)
        
        if not missing and not extra:
            print("✓ Schema matches model definition perfectly!")
        else:
            if missing:
                print(f"\n✗ Missing columns: {', '.join(sorted(missing))}")
            if extra:
                print(f"\n⚠ Extra columns (not in model): {', '.join(sorted(extra))}")
        
        print("\n" + "=" * 60)
    else:
        print("ERROR: 'indicators' table does not exist in database!")

