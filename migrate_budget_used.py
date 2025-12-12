"""
One-time migration script to copy budget_used to budget_used_year1 for all existing activities.
Run this script to migrate existing data.
"""
import os
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Activity, db

def migrate_budget_used():
    """Copy budget_used to budget_used_year1 for all activities where budget_used_year1 is 0 or None."""
    with app.app_context():
        try:
            activities = Activity.query.all()
            updated_count = 0
            
            for activity in activities:
                budget_used = getattr(activity, 'budget_used', None) or 0
                budget_used_year1 = getattr(activity, 'budget_used_year1', None) or 0
                
                # Only update if budget_used_year1 is 0 or None, and budget_used has a value
                if (budget_used_year1 == 0 or budget_used_year1 is None) and budget_used > 0:
                    activity.budget_used_year1 = budget_used
                    updated_count += 1
                    print(f"Updated activity {activity.id} (code: {activity.code}): budget_used_year1 = {budget_used}")
            
            if updated_count > 0:
                db.session.commit()
                print(f"\nMigration complete! Updated {updated_count} activities.")
            else:
                print("\nNo activities needed updating.")
                
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == "__main__":
    print("Starting budget_used to budget_used_year1 migration...")
    migrate_budget_used()
    print("Migration finished.")

