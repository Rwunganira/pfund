"""Utility functions for tracking user activity and usage."""

from datetime import datetime
from functools import wraps

from flask import request, session

from models import UserActivity, db


def log_user_activity(action, resource_type=None, resource_id=None, details=None):
    """Log a user activity to the database.
    
    Args:
        action: The action performed (e.g., "login", "view_activities", "create_activity")
        resource_type: Type of resource affected (e.g., "activity", "challenge")
        resource_id: ID of the resource if applicable
        details: Additional details about the action
    """
    user_id = session.get("user_id")
    if not user_id:
        return  # Don't log if user is not logged in
    
    try:
        activity = UserActivity(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            timestamp=datetime.utcnow()
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        # Log error but don't break the application
        print(f"Error logging user activity: {e}")
        db.session.rollback()


def track_activity(action, resource_type=None):
    """Decorator to automatically track user activity for a route.
    
    Usage:
        @activity_bp.route("/activity/new")
        @track_activity("create_activity", resource_type="activity")
        @admin_required
        def new_activity():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Log before executing the function
            resource_id = kwargs.get("activity_id") or kwargs.get("challenge_id") or kwargs.get("sub_id")
            log_user_activity(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator

