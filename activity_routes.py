from collections import defaultdict

from flask import Blueprint, flash, redirect, render_template, request, url_for, session
import tempfile

import pandas as pd
from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError

from auth_routes import admin_required, login_required, ADMIN_EMAIL
from models import Activity, Challenge, SubActivity, Indicator, db
from usage_tracking import log_user_activity


activity_bp = Blueprint("activity", __name__)


@activity_bp.route("/test")
def test():
    """Minimal test route to check if app is working."""
    return "App is working!"


@activity_bp.route("/")
@login_required
def index():
    """Simplified index route with maximum error handling."""
    # Log user activity
    log_user_activity("view_activities")
    
    # Start with absolute minimal setup
    try:
        # Try to get activities - if this fails, use empty list
        try:
            activities = Activity.query.order_by(Activity.code).all()
            
            # One-time migration: Sync budget_used_year1 from budget_used for existing records
            # This handles records that existed before the new columns were added
            # Note: We keep this migration for backward compatibility, but all calculations use year-specific fields
            needs_commit = False
            for a in activities:
                if a and (not getattr(a, 'budget_used_year1', None) or getattr(a, 'budget_used_year1', None) == 0):
                    budget_used = getattr(a, 'budget_used', None) or 0
                    if budget_used and budget_used > 0:
                        a.budget_used_year1 = budget_used
                        needs_commit = True
            
            if needs_commit:
                try:
                    db.session.commit()
                    print("Migrated budget_used to budget_used_year1 for existing records")
                except Exception as e:
                    print(f"Error migrating budget data: {e}")
                    db.session.rollback()
                    
        except Exception as db_error:
            import traceback
            print(f"Database error: {db_error}")
            print(traceback.format_exc())
            activities = []
        
        # Get filters and search term - support multiple values
        # Use getlist() to handle multiple checkbox selections
        status_list = request.args.getlist("status")
        entity_list = request.args.getlist("implementing_entity")
        category_list = request.args.getlist("category")
        results_list = request.args.getlist("results_area")
        search_query = request.args.get("q", "") or ""
        
        # For backward compatibility and display, also keep string versions (comma-separated)
        status_filter = ",".join(status_list) if status_list else ""
        entity_filter = ",".join(entity_list) if entity_list else ""
        category_filter = ",".join(category_list) if category_list else ""
        results_filter = ",".join(results_list) if results_list else ""

        # Apply filters if provided
        try:
            if status_list:
                activities = [a for a in activities if getattr(a, "status", None) in status_list]
            if entity_list:
                activities = [a for a in activities if getattr(a, "implementing_entity", None) in entity_list]
            if category_list:
                activities = [a for a in activities if getattr(a, "category", None) in category_list]
            if results_list:
                activities = [a for a in activities if getattr(a, "results_area", None) in results_list]
            
            if search_query:
                q = search_query.lower()
                filtered = []
                for a in activities:
                    if not a:
                        continue
                    # Search over a few key text fields
                    fields = [
                        getattr(a, "code", None),
                        getattr(a, "initial_activity", None),
                        getattr(a, "proposed_activity", None),
                        getattr(a, "implementing_entity", None),
                        getattr(a, "results_area", None),
                        getattr(a, "category", None),
                    ]
                    combined = " ".join([str(f) for f in fields if f]) .lower()
                    if q in combined:
                        filtered.append(a)
                activities = filtered
        except Exception as e:
            import traceback
            print(f"Error applying filters: {e}")
            print(traceback.format_exc())
                
    except Exception as e:
        import traceback
        print(f"Error in index route: {e}")
        print(traceback.format_exc())
        activities = []
        status_filter = ""
        entity_filter = ""

    # Summary metrics computed in Python
    try:
        import math
        
        def safe_float(value, default=0.0):
            """Safely convert value to float, handling None, NaN, and invalid values."""
            if value is None:
                return default
            try:
                if isinstance(value, float) and math.isnan(value):
                    return default
            except (TypeError, ValueError):
                pass
            try:
                val = float(value)
                if math.isnan(val) or math.isinf(val):
                    return default
                return val
            except (ValueError, TypeError):
                return default
        
        total_activities = len(activities) if activities else 0
        
        # Calculate budgets by year
        total_budget_year1 = 0.0
        total_budget_year2 = 0.0
        total_budget_year3 = 0.0
        total_budget = 0.0
        
        total_used_year1 = 0.0
        total_used_year2 = 0.0
        total_used_year3 = 0.0
        total_used = 0.0
        
        for a in activities:
            if a:
                # Allocated budgets
                budget_year1 = safe_float(getattr(a, 'budget_year1', None), 0.0)
                budget_year2 = safe_float(getattr(a, 'budget_year2', None), 0.0)
                budget_year3 = safe_float(getattr(a, 'budget_year3', None), 0.0)
                budget_total = safe_float(getattr(a, 'budget_total', None), 0.0)
                
                total_budget_year1 += budget_year1
                total_budget_year2 += budget_year2
                total_budget_year3 += budget_year3
                total_budget += budget_total
                
                # Used budgets
                used_year1 = safe_float(getattr(a, 'budget_used_year1', None), 0.0)
                used_year2 = safe_float(getattr(a, 'budget_used_year2', None), 0.0)
                used_year3 = safe_float(getattr(a, 'budget_used_year3', None), 0.0)
                
                total_used_year1 += used_year1
                total_used_year2 += used_year2
                total_used_year3 += used_year3
                total_used += (used_year1 + used_year2 + used_year3)
        
        # Calculate execution percentages
        exec_pct_year1 = (total_used_year1 / total_budget_year1 * 100) if total_budget_year1 > 0 else 0.0
        exec_pct_total = (total_used / total_budget * 100) if total_budget > 0 else 0.0
        
        # Calculate average progress
        avg_progress = (
            sum((a.progress or 0) for a in activities) / total_activities
            if total_activities > 0
            else 0
        )
        
        summary = {
            "total_activities": total_activities,
            "total_budget": safe_float(total_budget, 0.0),
            "total_used": safe_float(total_used, 0.0),
            "total_budget_year1": safe_float(total_budget_year1, 0.0),
            "total_used_year1": safe_float(total_used_year1, 0.0),
            "exec_pct_year1": safe_float(exec_pct_year1, 0.0),
            "exec_pct_total": safe_float(exec_pct_total, 0.0),
            "avg_progress": avg_progress,
        }
    except Exception as e:
        import traceback
        print(f"Error computing summary: {e}")
        print(traceback.format_exc())
        summary = {
            "total_activities": 0, 
            "total_budget": 0, 
            "total_used": 0, 
            "total_budget_year1": 0,
            "total_used_year1": 0,
            "exec_pct_year1": 0.0,
            "exec_pct_total": 0.0,
            "avg_progress": 0
        }

    # Breakdown by status
    try:
        by_status = defaultdict(lambda: {"count": 0, "budget": 0.0})
        for a in activities:
            if a:
                key = a.status or "Unknown"
                by_status[key]["count"] += 1
                by_status[key]["budget"] += a.budget_total or 0

        status_rows = [
            {"status": status, "count": data["count"], "budget": data["budget"]}
            for status, data in sorted(by_status.items())
        ]
    except Exception as e:
        import traceback
        print(f"Error computing status breakdown: {e}")
        print(traceback.format_exc())
        status_rows = []

    # For filter dropdowns (distinct implementing_entity)
    try:
        entities = [
            row[0]
            for row in db.session.query(Activity.implementing_entity)
            .filter(
                Activity.implementing_entity.isnot(None),
                Activity.implementing_entity != "",
            )
            .distinct()
            .order_by(Activity.implementing_entity)
            .all()
        ]
    except Exception as e:
        # If query fails, get entities from activities list
        import traceback
        print(f"Error fetching entities: {e}")
        print(traceback.format_exc())
        entities = list(set([a.implementing_entity for a in activities if a.implementing_entity]))
        entities.sort()

    # Compute per-activity budget execution percentage and overall summary safely
    try:
        # Attach a computed execution percentage and total budget used to each activity
        for a in activities or []:
            try:
                total = getattr(a, "budget_total", None) or 0
                # Calculate total used from all years - use only year-specific fields
                used_year1 = getattr(a, "budget_used_year1", None) or 0
                used_year2 = getattr(a, "budget_used_year2", None) or 0
                used_year3 = getattr(a, "budget_used_year3", None) or 0
                used = used_year1 + used_year2 + used_year3
                a.exec_pct = round((used / total) * 100) if total > 0 else 0
                # Store total budget used (sum of all years) for display
                a.total_budget_used = used
            except Exception:
                a.exec_pct = 0
                a.total_budget_used = 0

        total_activities = len(activities) if activities else 0
        total_budget = sum((getattr(a, "budget_total", None) or 0) for a in activities) if activities else 0
        # Calculate total_used from all years - use only year-specific fields
        total_used = sum(
            (getattr(a, 'budget_used_year1', None) or 0) + 
            (getattr(a, 'budget_used_year2', None) or 0) + 
            (getattr(a, 'budget_used_year3', None) or 0)
            for a in activities
        ) if activities else 0
        # Average progress now reflects average budget execution percentage
        avg_progress = (
            sum((getattr(a, "exec_pct", 0) or 0) for a in activities) / total_activities
            if total_activities > 0
            else 0
        )
        summary = {
            "total_activities": total_activities,
            "total_budget": total_budget,
            "total_used": total_used,
            "avg_progress": avg_progress,
        }
    except Exception as e:
        import traceback
        print(f"Error computing summary: {e}")
        print(traceback.format_exc())
        summary = {
            "total_activities": 0, 
            "total_budget": 0, 
            "total_used": 0, 
            "total_budget_year1": 0,
            "total_used_year1": 0,
            "exec_pct_year1": 0.0,
            "exec_pct_total": 0.0,
            "avg_progress": 0
        }

    # Status breakdown
    try:
        by_status = {}
        for a in activities:
            if a:
                key = getattr(a, 'status', None) or "Unknown"
                if key not in by_status:
                    by_status[key] = {"count": 0, "budget": 0.0}
                by_status[key]["count"] += 1
                by_status[key]["budget"] += getattr(a, 'budget_total', None) or 0
        status_rows = [{"status": k, "count": v["count"], "budget": v["budget"]} for k, v in sorted(by_status.items())]
    except Exception as e:
        import traceback
        print(f"Error computing status breakdown: {e}")
        print(traceback.format_exc())
        status_rows = []

    # Budget execution by year - use filtered activities so filters affect the calculation
    try:
        import math
        # Use the filtered activities list (same as what's displayed in the table)
        # This ensures budget execution by year reflects the current filters
        
        budget_by_year = {
            "year1": {"allocated": 0.0, "used": 0.0, "execution_pct": 0.0},
            "year2": {"allocated": 0.0, "used": 0.0, "execution_pct": 0.0},
            "year3": {"allocated": 0.0, "used": 0.0, "execution_pct": 0.0},
        }
        
        def safe_float(value, default=0.0):
            """Safely convert value to float, handling None, NaN, and invalid values."""
            if value is None:
                return default
            # Check if value is already NaN (can happen when reading from database)
            try:
                if isinstance(value, float) and math.isnan(value):
                    return default
            except (TypeError, ValueError):
                pass
            try:
                val = float(value)
                if math.isnan(val) or math.isinf(val):
                    return default
                return val
            except (ValueError, TypeError):
                return default
        
        for a in activities:
            if a:
                budget_year1 = safe_float(getattr(a, 'budget_year1', None), 0.0)
                budget_year2 = safe_float(getattr(a, 'budget_year2', None), 0.0)
                budget_year3 = safe_float(getattr(a, 'budget_year3', None), 0.0)
                
                # Get actual used budgets per year (new fields)
                budget_used_year1 = safe_float(getattr(a, 'budget_used_year1', None), 0.0)
                budget_used_year2 = safe_float(getattr(a, 'budget_used_year2', None), 0.0)
                budget_used_year3 = safe_float(getattr(a, 'budget_used_year3', None), 0.0)
                
                # Sum allocated budgets by year
                budget_by_year["year1"]["allocated"] += budget_year1
                budget_by_year["year2"]["allocated"] += budget_year2
                budget_by_year["year3"]["allocated"] += budget_year3
                
                # Sum actual used budgets by year
                budget_by_year["year1"]["used"] += budget_used_year1
                budget_by_year["year2"]["used"] += budget_used_year2
                budget_by_year["year3"]["used"] += budget_used_year3
        
        # Calculate execution percentages and ensure no NaN values
        for year_data in budget_by_year.values():
            allocated = safe_float(year_data["allocated"], 0.0)
            used = safe_float(year_data["used"], 0.0)
            
            # Ensure allocated and used are valid before calculation
            allocated = max(0.0, allocated)  # Ensure non-negative
            used = max(0.0, used)  # Ensure non-negative
            
            if allocated > 0:
                execution_pct = (used / allocated) * 100
                year_data["execution_pct"] = safe_float(execution_pct, 0.0)
            else:
                year_data["execution_pct"] = 0.0
            
            # Final validation - ensure all values are valid numbers and not NaN
            year_data["allocated"] = safe_float(allocated, 0.0)
            year_data["used"] = safe_float(used, 0.0)
            year_data["execution_pct"] = safe_float(year_data["execution_pct"], 0.0)
            
            # Double-check: if any value is still NaN, force to 0
            if math.isnan(year_data["allocated"]):
                year_data["allocated"] = 0.0
            if math.isnan(year_data["used"]):
                year_data["used"] = 0.0
            if math.isnan(year_data["execution_pct"]):
                year_data["execution_pct"] = 0.0
        
        # Calculate execution percentages for each year (non-cumulative)
        year1_allocated = safe_float(budget_by_year["year1"]["allocated"], 0.0)
        year1_used = safe_float(budget_by_year["year1"]["used"], 0.0)
        year1_exec_pct = (year1_used / year1_allocated * 100) if year1_allocated > 0 else 0.0
        
        year2_allocated = safe_float(budget_by_year["year2"]["allocated"], 0.0)
        year2_used = safe_float(budget_by_year["year2"]["used"], 0.0)
        year2_exec_pct = (year2_used / year2_allocated * 100) if year2_allocated > 0 else 0.0
        
        year3_allocated = safe_float(budget_by_year["year3"]["allocated"], 0.0)
        year3_used = safe_float(budget_by_year["year3"]["used"], 0.0)
        year3_exec_pct = (year3_used / year3_allocated * 100) if year3_allocated > 0 else 0.0
        
        # Calculate totals across all years
        total_allocated = year1_allocated + year2_allocated + year3_allocated
        total_used = year1_used + year2_used + year3_used
        total_exec_pct = (total_used / total_allocated * 100) if total_allocated > 0 else 0.0
        
        budget_execution_by_year = [
            {"year": "Year 1", "allocated": safe_float(year1_allocated, 0.0), 
             "used": safe_float(year1_used, 0.0), 
             "execution_pct": safe_float(year1_exec_pct, 0.0)},
            {"year": "Year 2", "allocated": safe_float(year2_allocated, 0.0), 
             "used": safe_float(year2_used, 0.0), 
             "execution_pct": safe_float(year2_exec_pct, 0.0)},
            {"year": "Year 3", "allocated": safe_float(year3_allocated, 0.0), 
             "used": safe_float(year3_used, 0.0), 
             "execution_pct": safe_float(year3_exec_pct, 0.0)},
        ]
        
        budget_execution_total = {
            "allocated": safe_float(total_allocated, 0.0),
            "used": safe_float(total_used, 0.0),
            "execution_pct": safe_float(total_exec_pct, 0.0)
        }
    except Exception as e:
        import traceback
        print(f"Error computing budget execution by year: {e}")
        print(traceback.format_exc())
        budget_execution_by_year = []
        budget_execution_total = {"allocated": 0.0, "used": 0.0, "execution_pct": 0.0}

    # Entities for filter
    try:
        entities = sorted(list(set([getattr(a, 'implementing_entity', None) for a in activities if getattr(a, 'implementing_entity', None)])))
    except:
        entities = []

    # Categories (activity type) for filter
    try:
        categories = sorted(list(set([getattr(a, 'category', None) for a in activities if getattr(a, 'category', None)])))
    except:
        categories = []

    # Results areas for filter
    try:
        results_areas = sorted(list(set([getattr(a, 'results_area', None) for a in activities if getattr(a, 'results_area', None)])))
    except:
        results_areas = []

    # Generate URLs - create both dictionary and list formats
    try:
        activity_urls = {}
        activities_with_urls = []
        for a in activities:
            if a and hasattr(a, 'id'):
                aid = getattr(a, 'id', None)
                if aid:  # Only process if ID exists
                    # Create URL dictionary for template
                    activity_urls[aid] = {
                        'edit_url': f'/activity/{aid}/edit',
                        'delete_url': f'/activity/{aid}/delete'
                    }
                    # Create list for JavaScript data
                    activities_with_urls.append({
                        'activity': a,
                        'edit_url': f'/activity/{aid}/edit'
                    })
        print(f"Generated URLs for {len(activities_with_urls)} activities")
    except Exception as e:
        import traceback
        print(f"Error generating URLs: {e}")
        print(traceback.format_exc())
        activity_urls = {}
        activities_with_urls = []

    # Render template with all variables
    try:
        return render_template(
            "index.html",
            activities=activities or [],
            activities_with_urls=activities_with_urls or [],
            activity_urls=activity_urls or {},
            summary=summary,
            status_rows=status_rows or [],
            budget_execution_by_year=budget_execution_by_year or [],
            budget_execution_total=budget_execution_total,
            status_filter=status_filter or "",
            entity_filter=entity_filter or "",
            category_filter=category_filter or "",
            results_filter=results_filter or "",
            search_query=search_query or "",
            entities=entities or [],
            categories=categories or [],
            results_areas=results_areas or [],
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"CRITICAL: Template rendering error: {e}")
        print(error_trace)
        # Return a simple HTML response instead of crashing
        return f"""
        <html>
        <body>
        <h1>Template Error</h1>
        <p>Error: {str(e)}</p>
        <pre>{error_trace}</pre>
        <p>Activities count: {len(activities) if activities else 0}</p>
        </body>
        </html>
        """, 500


@activity_bp.route("/activity/new", methods=["GET", "POST"])
@admin_required
def new_activity():
    if request.method == "POST":
        data = {
            "code": request.form.get("code") or None,
            "initial_activity": request.form.get("initial_activity") or None,
            "proposed_activity": request.form.get("proposed_activity") or None,
            "implementing_entity": request.form.get("implementing_entity") or None,
            "delivery_partner": request.form.get("delivery_partner") or None,
            "results_area": request.form.get("results_area") or None,
            "category": request.form.get("category") or None,
            "budget_year1": request.form.get("budget_year1") or 0,
            "budget_total": request.form.get("budget_total") or 0,
            "budget_year2": request.form.get("budget_year2") or 0,
            "budget_year3": request.form.get("budget_year3") or 0,
            "budget_used_year1": request.form.get("budget_used_year1") or 0,
            "budget_used_year2": request.form.get("budget_used_year2") or 0,
            "budget_used_year3": request.form.get("budget_used_year3") or 0,
            "status": request.form.get("status") or "Planned",
            "progress": request.form.get("progress") or 0,
            "notes": request.form.get("notes") or None,
        }

        # Get budget used values per year - use only year-specific fields for all calculations
        budget_used_year1 = float(data["budget_used_year1"] or 0)
        budget_used_year2 = float(data["budget_used_year2"] or 0)
        budget_used_year3 = float(data["budget_used_year3"] or 0)

        # Auto-calculate progress from total budget used (all years) and budget_total
        budget_total = float(data["budget_total"] or 0)
        total_budget_used = budget_used_year1 + budget_used_year2 + budget_used_year3
        progress = int(round((total_budget_used / budget_total) * 100)) if budget_total > 0 else 0
        
        activity = Activity(
            code=data["code"],
            initial_activity=data["initial_activity"],
            proposed_activity=data["proposed_activity"],
            implementing_entity=data["implementing_entity"],
            delivery_partner=data["delivery_partner"],
            results_area=data["results_area"],
            category=data["category"],
            budget_year1=float(data["budget_year1"] or 0),
            budget_year2=float(data["budget_year2"] or 0),
            budget_year3=float(data["budget_year3"] or 0),
            budget_total=budget_total,
            budget_used=budget_used_year1,  # Keep for backward compatibility only
            budget_used_year1=budget_used_year1,
            budget_used_year2=budget_used_year2,
            budget_used_year3=budget_used_year3,
            status=data["status"],
            progress=progress,
            notes=data["notes"],
        )
        db.session.add(activity)
        db.session.commit()
        log_user_activity("create_activity", resource_type="activity", resource_id=activity.id)
        flash("Activity created successfully", "success")
        return redirect(url_for("activity.index"))

    return render_template("form.html", activity=None)


@activity_bp.route("/activity/<int:activity_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_activity(activity_id):
    activity = Activity.query.get(activity_id)

    if not activity:
        flash("Activity not found", "error")
        return redirect(url_for("activity.index"))
    
    # Sync budget_used_year1 from budget_used if budget_used_year1 is 0 or None
    # This handles existing records that haven't been migrated yet
    # Note: We keep this migration for backward compatibility, but all calculations use year-specific fields
    if activity and (not activity.budget_used_year1 or activity.budget_used_year1 == 0):
        if activity.budget_used and activity.budget_used > 0:
            activity.budget_used_year1 = activity.budget_used
            db.session.commit()

    if request.method == "POST":
        data = {
            "code": request.form.get("code") or None,
            "initial_activity": request.form.get("initial_activity") or None,
            "proposed_activity": request.form.get("proposed_activity") or None,
            "implementing_entity": request.form.get("implementing_entity") or None,
            "delivery_partner": request.form.get("delivery_partner") or None,
            "results_area": request.form.get("results_area") or None,
            "category": request.form.get("category") or None,
            "budget_year1": request.form.get("budget_year1") or 0,
            "budget_total": request.form.get("budget_total") or 0,
            "budget_year2": request.form.get("budget_year2") or 0,
            "budget_year3": request.form.get("budget_year3") or 0,
            "budget_used_year1": request.form.get("budget_used_year1") or 0,
            "budget_used_year2": request.form.get("budget_used_year2") or 0,
            "budget_used_year3": request.form.get("budget_used_year3") or 0,
            "status": request.form.get("status") or "Planned",
            "progress": request.form.get("progress") or 0,
            "notes": request.form.get("notes") or None,
        }

        # Get budget used values per year - use only year-specific fields for all calculations
        budget_used_year1 = float(data["budget_used_year1"] or 0)
        budget_used_year2 = float(data["budget_used_year2"] or 0)
        budget_used_year3 = float(data["budget_used_year3"] or 0)

        activity.code = data["code"]
        activity.initial_activity = data["initial_activity"]
        activity.proposed_activity = data["proposed_activity"]
        activity.implementing_entity = data["implementing_entity"]
        activity.delivery_partner = data["delivery_partner"]
        activity.results_area = data["results_area"]
        activity.category = data["category"]
        activity.budget_year1 = float(data["budget_year1"] or 0)
        activity.budget_year2 = float(data["budget_year2"] or 0)
        activity.budget_year3 = float(data["budget_year3"] or 0)
        activity.budget_total = float(data["budget_total"] or 0)
        activity.budget_used = budget_used_year1  # Keep for backward compatibility only
        activity.budget_used_year1 = budget_used_year1
        activity.budget_used_year2 = budget_used_year2
        activity.budget_used_year3 = budget_used_year3
        activity.status = data["status"]
        # Auto-calculate progress from total budget used (all years) and budget_total
        budget_total = activity.budget_total or 0
        total_budget_used = budget_used_year1 + budget_used_year2 + budget_used_year3
        activity.progress = int(round((total_budget_used / budget_total) * 100)) if budget_total > 0 else 0
        activity.notes = data["notes"]

        db.session.commit()
        log_user_activity("edit_activity", resource_type="activity", resource_id=activity_id)
        flash("Activity updated successfully", "success")

        # If we came from a filtered view, go back there
        next_url = request.args.get("next")
        if next_url:
            return redirect(next_url)
        return redirect(url_for("activity.index"))

    return render_template("form.html", activity=activity)


@activity_bp.route("/challenges/new", methods=["POST"])
@admin_required
def add_challenge():
    """Add a new implementation challenge row."""
    try:
        challenge_text = (request.form.get("challenge") or "").strip()
        action_text = (request.form.get("action") or "").strip()
        responsible = (request.form.get("responsible") or "").strip()
        timeline = (request.form.get("timeline") or "").strip()
        status = (request.form.get("status") or "pending").strip().lower()

        if not challenge_text or not action_text:
            flash("Please provide both a challenge and an action.", "error")
            return redirect(request.form.get("next") or url_for("activity.index"))

        # Validate status
        if status not in ["pending", "completed", "canceled"]:
            status = "pending"

        # Check if status column exists (for backward compatibility)
        try:
            ch = Challenge(
                challenge=challenge_text,
                action=action_text,
                responsible=responsible or None,
                timeline=timeline or None,
                status=status,
            )
        except Exception as e:
            # If status column doesn't exist, create without it
            import traceback
            print(f"Error creating challenge with status: {e}")
            print(traceback.format_exc())
            ch = Challenge(
                challenge=challenge_text,
                action=action_text,
                responsible=responsible or None,
                timeline=timeline or None,
            )
        
        db.session.add(ch)
        db.session.commit()
        flash("Challenge added.", "success")

    except Exception as e:
        import traceback
        print(f"Error adding challenge: {e}")
        print(traceback.format_exc())
        db.session.rollback()
        flash("An error occurred while adding the challenge. Please check the logs.", "error")

    return redirect(request.form.get("next") or url_for("activity.challenges_page"))


@activity_bp.route("/challenges", methods=["GET"])
@login_required
def challenges_page():
    """Standalone page for viewing and managing implementation challenges."""
    try:
        challenges = Challenge.query.order_by(Challenge.id.desc()).all()
    except Exception as e:
        import traceback
        print(f"Error loading challenges on challenges_page: {e}")
        print(traceback.format_exc())
        challenges = []

    return render_template("challenges.html", challenges=challenges, admin_email=ADMIN_EMAIL)


@activity_bp.route("/challenges/download", methods=["GET"])
@login_required
def download_challenges():
    """Download all challenges as a CSV file."""
    # Build CSV in memory
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "challenge",
            "action",
            "responsible",
            "timeline",
            "status",
        ]
    )

    rows = Challenge.query.order_by(Challenge.id).all()
    for c in rows:
        writer.writerow(
            [
                c.challenge or "",
                c.action or "",
                c.responsible or "",
                c.timeline or "",
                c.status or "",
            ]
        )

    from flask import Response

    output.seek(0)
    return Response(
        output.read(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=challenges.csv",
        },
    )


@activity_bp.route("/challenges/upload", methods=["POST"])
@admin_required
def upload_challenges():
    """Upload an Excel file and bulk-insert/update challenges."""
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("No file selected for challenges upload.", "error")
        return redirect(url_for("activity.challenges_page"))

    if not (file.filename.lower().endswith(".xlsx") or file.filename.lower().endswith(".xls")):
        flash("Please upload an Excel file (.xlsx or .xls) for challenges.", "error")
        return redirect(url_for("activity.challenges_page"))

    try:
        # Save to a temporary file so pandas can read it
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file.save(tmp.name)
            import pandas as pd  # local import in case global changes

            df = pd.read_excel(tmp.name, dtype=str)

        # Normalise column names
        columns = list(df.columns)
        lower_map = {str(c).strip().lower(): c for c in columns}

        def get_val(row, *names):
            for n in names:
                key = str(n).strip().lower()
                col = lower_map.get(key)
                if not col:
                    # fallback: partial match
                    for c in columns:
                        if key in str(c).strip().lower():
                            col = c
                            break
                if col and col in row:
                    val = row[col]
                    if isinstance(val, str):
                        val = val.strip()
                    if val not in (None, "", "nan"):
                        return str(val)
            return None

        created = 0
        updated = 0
        for _, row in df.iterrows():
            challenge_text = get_val(row, "challenge")
            action_text = get_val(row, "action", "agreed action")
            responsible = get_val(row, "responsible")
            timeline = get_val(row, "timeline")
            status = (get_val(row, "status") or "pending").strip().lower()

            if not challenge_text or not action_text:
                continue

            if status not in ["pending", "completed", "canceled"]:
                status = "pending"

            # Use challenge + action as a simple uniqueness key for updating
            existing = (
                Challenge.query.filter_by(challenge=challenge_text, action=action_text).first()
            )
            if existing:
                existing.responsible = responsible or None
                existing.timeline = timeline or None
                existing.status = status
                updated += 1
            else:
                ch = Challenge(
                    challenge=challenge_text,
                    action=action_text,
                    responsible=responsible or None,
                    timeline=timeline or None,
                    status=status,
                )
                db.session.add(ch)
                created += 1

        db.session.commit()
        if created or updated:
            flash(
                f"Challenges import complete. Created {created}, updated {updated}.",
                "success",
            )
        else:
            flash("No valid challenge rows found in the uploaded file.", "info")
    except Exception as exc:  # pylint: disable=broad-except
        import traceback

        print(f"Error reading challenges file: {exc}")
        print(traceback.format_exc())
        db.session.rollback()
        flash(f"Error reading challenges file: {exc}", "error")

    return redirect(url_for("activity.challenges_page"))


@activity_bp.route("/challenges/<int:challenge_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_challenge(challenge_id):
    """Edit an existing challenge."""
    challenge = Challenge.query.get_or_404(challenge_id)
    
    if request.method == "POST":
        try:
            challenge.challenge = (request.form.get("challenge") or "").strip()
            challenge.action = (request.form.get("action") or "").strip()
            challenge.responsible = (request.form.get("responsible") or "").strip() or None
            challenge.timeline = (request.form.get("timeline") or "").strip() or None
            status = (request.form.get("status") or "pending").strip().lower()
            
            if not challenge.challenge or not challenge.action:
                flash("Please provide both a challenge and an action.", "error")
                return redirect(url_for("activity.edit_challenge", challenge_id=challenge_id))
            
            # Validate status
            if status not in ["pending", "completed", "canceled"]:
                status = "pending"
            challenge.status = status
            
            db.session.commit()
            flash("Challenge updated.", "success")
            return redirect(request.form.get("next") or url_for("activity.challenges_page"))
            
        except Exception as e:
            import traceback
            print(f"Error updating challenge: {e}")
            print(traceback.format_exc())
            db.session.rollback()
            flash("An error occurred while updating the challenge.", "error")
            return redirect(url_for("activity.edit_challenge", challenge_id=challenge_id))
    
    # GET request - show edit form
    return render_template("challenge_form.html", challenge=challenge, is_edit=True)


@activity_bp.route("/challenges/<int:challenge_id>/delete", methods=["POST"])
@admin_required
def delete_challenge(challenge_id):
    """Delete a challenge. Only superadmin can delete."""
    # Only the super admin (configured admin email) can delete.
    if session.get("email") != ADMIN_EMAIL:
        flash("Only the super administrator can delete challenges.", "error")
        return redirect(url_for("activity.challenges_page"))
    
    challenge = Challenge.query.get(challenge_id)
    if challenge:
        db.session.delete(challenge)
        db.session.commit()
        flash("Challenge deleted.", "info")
    else:
        flash("Challenge not found.", "error")
    return redirect(request.form.get("next") or url_for("activity.challenges_page"))


@activity_bp.route("/activity/<int:activity_id>/delete", methods=["POST"])
@admin_required
def delete_activity(activity_id):
    # Only the super admin (configured admin email) can delete.
    if session.get("email") != ADMIN_EMAIL:
        flash("Only the super administrator can delete activities.", "error")
        return redirect(url_for("activity.index"))

    activity = Activity.query.get(activity_id)
    if activity:
        db.session.delete(activity)
        db.session.commit()
        log_user_activity("delete_activity", resource_type="activity", resource_id=activity_id)
        flash("Activity deleted", "info")
    else:
        flash("Activity not found.", "error")
    return redirect(url_for("activity.index"))


@activity_bp.route("/activities/delete_all", methods=["POST"])
@admin_required
def delete_all_activities():
    """Delete all activities from the database."""
    # Only the super admin (configured admin email) can delete everything.
    if session.get("email") != ADMIN_EMAIL:
        flash("Only the super administrator can delete all activities.", "error")
        return redirect(url_for("activity.index"))

    Activity.query.delete()
    db.session.commit()
    flash("All activities have been deleted.", "info")
    return redirect(url_for("activity.index"))


@activity_bp.route("/activity/<int:activity_id>/subactivities", methods=["GET", "POST"])
@admin_required
def manage_subactivities(activity_id):
    """View and create sub-activities for a given activity."""
    activity = Activity.query.get_or_404(activity_id)

    # Ensure the sub_activities table and status column exist (in case migrations haven't been applied)
    try:
        # Quick test query – if the table/column is missing, this will raise ProgrammingError
        _ = db.session.query(SubActivity).first()

        # Also ensure the status column exists (idempotent check)
        inspector = inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("sub_activities")]
        if "status" not in columns:
            db.session.execute(
                text(
                    "ALTER TABLE sub_activities "
                    "ADD COLUMN status VARCHAR(255) DEFAULT 'pending' NOT NULL"
                )
            )
            db.session.execute(
                text(
                    "UPDATE sub_activities SET status = 'pending' WHERE status IS NULL"
                )
            )
            db.session.commit()
    except ProgrammingError as e:
        # Always rollback the failed transaction first
        db.session.rollback()
        msg = str(e)
        # Table missing entirely
        if 'relation "sub_activities" does not exist' in msg:
            db.create_all()
        # Column missing on existing table
        elif "column sub_activities.status does not exist" in msg:
            db.session.execute(
                text(
                    "ALTER TABLE sub_activities "
                    "ADD COLUMN status VARCHAR(255) DEFAULT 'pending' NOT NULL"
                )
            )
            db.session.execute(
                text(
                    "UPDATE sub_activities SET status = 'pending' WHERE status IS NULL"
                )
            )
            db.session.commit()
        else:
            # Re-raise unexpected errors
            raise
    except Exception:
        # On any other error while inspecting/altering, rollback and continue;
        # the page will still work for rows without status.
        db.session.rollback()

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        responsible = (request.form.get("responsible") or "").strip()
        timeline = (request.form.get("timeline") or "").strip()
        status = (request.form.get("status") or "pending").strip().lower()

        if not title:
            flash("Sub-activity title is required.", "error")
            return redirect(url_for("activity.manage_subactivities", activity_id=activity_id))

        if status not in ["pending", "in-progress", "completed", "canceled"]:
            status = "pending"

        sub = SubActivity(
            activity_id=activity.id,
            title=title,
            responsible=responsible or None,
            timeline=timeline or None,
            status=status,
        )
        db.session.add(sub)
        db.session.commit()
        flash("Sub-activity added.", "success")
        return redirect(url_for("activity.manage_subactivities", activity_id=activity_id))

    # For display, load all sub-activities for this activity
    sub_activities = activity.sub_activities.order_by(SubActivity.id.asc()).all()
    return render_template(
        "subactivities.html",
        activity=activity,
        sub_activities=sub_activities,
        admin_email=ADMIN_EMAIL,
    )


@activity_bp.route("/subactivities/<int:sub_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_subactivity(sub_id):
    """Edit a single sub-activity (admin only)."""
    sub = SubActivity.query.get_or_404(sub_id)
    activity = sub.activity

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        responsible = (request.form.get("responsible") or "").strip()
        timeline = (request.form.get("timeline") or "").strip()
        status = (request.form.get("status") or "pending").strip().lower()

        if not title:
            flash("Sub-activity title is required.", "error")
            return redirect(url_for("activity.edit_subactivity", sub_id=sub_id))

        if status not in ["pending", "in-progress", "completed", "canceled"]:
            status = "pending"

        sub.title = title
        sub.responsible = responsible or None
        sub.timeline = timeline or None
        # Guard against older DBs without the column
        try:
            sub.status = status
        except Exception:
            pass

        db.session.commit()
        flash("Sub-activity updated.", "success")
        return redirect(url_for("activity.manage_subactivities", activity_id=activity.id))

    return render_template(
        "subactivity_form.html",
        subactivity=sub,
        activity=activity,
        is_edit=True,
    )


@activity_bp.route("/subactivities/<int:sub_id>/delete", methods=["POST"])
@admin_required
def delete_subactivity(sub_id):
    """Delete a sub-activity. Only superadmin can delete."""
    # Only the super admin (configured admin email) can delete.
    if session.get("email") != ADMIN_EMAIL:
        flash("Only the super administrator can delete sub-activities.", "error")
        return redirect(url_for("activity.index"))

    sub = SubActivity.query.get(sub_id)
    if sub:
        activity_id = sub.activity_id
        db.session.delete(sub)
        db.session.commit()
        flash("Sub-activity deleted.", "info")
        return redirect(url_for("activity.manage_subactivities", activity_id=activity_id))
    else:
        flash("Sub-activity not found.", "error")
        return redirect(url_for("activity.index"))


@activity_bp.route("/upload", methods=["POST"])
@admin_required
def upload_excel():
    """Upload an Excel file and bulk-insert activities."""
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("activity.index"))

    if not (file.filename.lower().endswith(".xlsx") or file.filename.lower().endswith(".xls")):
        flash("Please upload an Excel file (.xlsx or .xls).", "error")
        return redirect(url_for("activity.index"))

    try:
        # Save to a temporary file so pandas can read it
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file.save(tmp.name)
            # Read as text so codes like "act001" are preserved exactly
            df = pd.read_excel(tmp.name, dtype=str)

        # Build a helper map so we can match column names case-insensitively
        columns = list(df.columns)
        lower_map = {str(c).strip().lower(): c for c in columns}

        # Expected column names based on your sheet
        def get_val(row, *names):
            for n in names:
                key = str(n).strip().lower()
                col = lower_map.get(key)
                if not col:
                    # fallback: try partial match like anything containing the key
                    for c in columns:
                        if key in str(c).strip().lower():
                            col = c
                            break
                if col and col in row:
                    val = row[col]
                    if isinstance(val, str):
                        val = val.strip()
                    if val not in (None, "", "nan", ""):
                        return str(val)
            return None

        rows_to_insert = []
        for _, row in df.iterrows():
            code = get_val(row, "code", "code_new_improved_noch")
            initial_activity = get_val(row, "Initial activities", "Initial Activity")
            proposed_activity = get_val(row, "New Proposed Project Activity", "Proposed Activity")
            implementing_entity = get_val(row, "IE in charge of impl", "Implementing Entity")
            delivery_partner = get_val(row, "Delivery partner")
            results_area = get_val(row, "results_area", "Results Area")
            category = get_val(row, "sr_category", "Category")
            notes = get_val(row, "Notes", "Note", "Comments")

            def get_num(row, *names):
                for n in names:
                    key = str(n).strip().lower()
                    col = lower_map.get(key)
                    if col and col in row and row[col] not in (None, "", "nan"):
                        try:
                            return float(row[col])
                        except ValueError:
                            continue
                return 0.0

            budget_year1 = get_num(row, "Sum of adjusted_bdg_year1", "Budget Y1", "budget_year1")
            budget_year2 = get_num(row, "Sum of adjusted_bdg_year2", "Budget Y2", "budget_year2")
            budget_year3 = get_num(row, "Sum of adjusted_bdg_year3", "Budget Y3", "budget_year3")
            budget_total = get_num(row, "Sum of TOTAL", "Total Budget", "budget_total")
            
            # Try to read year-specific budget used columns first
            budget_used_year1 = get_num(row, "Budget Used Year 1", "budget_used_year1", "Budget used Year 1")
            budget_used_year2 = get_num(row, "Budget Used Year 2", "budget_used_year2", "Budget used Year 2")
            budget_used_year3 = get_num(row, "Budget Used Year 3", "budget_used_year3", "Budget used Year 3")
            
            # If year-specific columns are not found, fall back to "Budget used" for year 1 (backward compatibility)
            if budget_used_year1 == 0.0 and budget_used_year2 == 0.0 and budget_used_year3 == 0.0:
                budget_used_from_file = get_num(row, "Budget used", "Budget Used", "budget_used")
                budget_used_year1 = budget_used_from_file
                budget_used_year2 = 0.0
                budget_used_year3 = 0.0

            # Default status and progress for imported rows
            status = "Planned"
            # Calculate progress from total budget used (all years) and budget_total
            total_budget_used = budget_used_year1 + budget_used_year2 + budget_used_year3
            progress = int(round((total_budget_used / budget_total) * 100)) if budget_total > 0 else 0

            # Skip completely empty rows
            if not any([code, initial_activity, proposed_activity]):
                continue

            rows_to_insert.append(
                (
                    code,
                    initial_activity,
                    proposed_activity,
                    implementing_entity,
                    delivery_partner,
                    results_area,
                    category,
                    budget_year1,
                    budget_year2,
                    budget_year3,
                    budget_total,
                    budget_used_year1,  # Use year1 for backward compatibility
                    budget_used_year1,
                    budget_used_year2,
                    budget_used_year3,
                    status,
                    progress,
                    notes,
                )
            )

        if rows_to_insert:
            created = 0
            updated = 0
            for row in rows_to_insert:
                (
                    code,
                    initial_activity,
                    proposed_activity,
                    implementing_entity,
                    delivery_partner,
                    results_area,
                    category,
                    budget_year1,
                    budget_year2,
                    budget_year3,
                    budget_total,
                    budget_used,  # This is budget_used_year1 for backward compatibility
                    budget_used_year1,
                    budget_used_year2,
                    budget_used_year3,
                    status,
                    progress,
                    notes,
                ) = row

                existing = None
                if code:
                    existing = Activity.query.filter_by(code=code).first()
                if existing:
                    # Update existing record - use only year-specific fields for calculations
                    existing.initial_activity = initial_activity
                    existing.proposed_activity = proposed_activity
                    existing.implementing_entity = implementing_entity
                    existing.delivery_partner = delivery_partner
                    existing.results_area = results_area
                    existing.category = category
                    existing.budget_year1 = budget_year1
                    existing.budget_year2 = budget_year2
                    existing.budget_year3 = budget_year3
                    existing.budget_total = budget_total
                    existing.budget_used = budget_used_year1  # Keep for backward compatibility only
                    existing.budget_used_year1 = budget_used_year1
                    existing.budget_used_year2 = budget_used_year2
                    existing.budget_used_year3 = budget_used_year3
                    existing.status = status
                    existing.progress = progress
                    existing.notes = notes
                    updated += 1
                else:
                    activity = Activity(
                        code=code,
                        initial_activity=initial_activity,
                        proposed_activity=proposed_activity,
                        implementing_entity=implementing_entity,
                        delivery_partner=delivery_partner,
                        results_area=results_area,
                        category=category,
                        budget_year1=budget_year1,
                        budget_year2=budget_year2,
                        budget_year3=budget_year3,
                        budget_total=budget_total,
                        budget_used=budget_used_year1,  # Keep for backward compatibility only
                        budget_used_year1=budget_used_year1,
                        budget_used_year2=budget_used_year2,
                        budget_used_year3=budget_used_year3,
                        status=status,
                        progress=progress,
                        notes=notes,
                    )
                    db.session.add(activity)
                    created += 1

            db.session.commit()
            flash(f"Imported {created} new activities, updated {updated} existing.", "success")
        else:
            flash("No valid rows found in Excel file.", "info")
    except Exception as exc:  # pylint: disable=broad-except
        flash(f"Error reading Excel file: {exc}", "error")

    return redirect(url_for("activity.index"))


@activity_bp.route("/download", methods=["GET"])
@login_required
def download_activities():
    """Download all (filtered) activities as a CSV file."""
    log_user_activity("download_csv", resource_type="activities")
    # Support multiple filter values (from multi-select)
    status_list = request.args.getlist("status")
    entity_list = request.args.getlist("implementing_entity")
    category_list = request.args.getlist("category")
    results_list = request.args.getlist("results_area")
    search_query = request.args.get("q", "") or ""

    query = Activity.query
    
    # Apply filters
    if status_list:
        query = query.filter(Activity.status.in_(status_list))
    if entity_list:
        query = query.filter(Activity.implementing_entity.in_(entity_list))
    if category_list:
        query = query.filter(Activity.category.in_(category_list))
    if results_list:
        query = query.filter(Activity.results_area.in_(results_list))
    
    # Apply search query
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Activity.code.ilike(search_term),
                Activity.initial_activity.ilike(search_term),
                Activity.proposed_activity.ilike(search_term),
                Activity.implementing_entity.ilike(search_term),
                Activity.results_area.ilike(search_term),
                Activity.category.ilike(search_term),
            )
        )

    activities = query.order_by(Activity.code).all()

    # Build CSV in memory
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "code",
            "initial_activity",
            "proposed_activity",
            "implementing_entity",
            "delivery_partner",
            "results_area",
            "category",
            "budget_year1",
            "budget_year2",
            "budget_year3",
            "budget_total",
            "budget_used",  # Keep for backward compatibility (stores Year 1 only)
            "budget_used_year1",
            "budget_used_year2",
            "budget_used_year3",
            "status",
            "progress",
            "notes",
        ]
    )
    for a in activities:
        # Auto-calculate progress from total budget used (all years) and budget_total
        # Use only year-specific fields for all calculations
        budget_total = a.budget_total or 0
        budget_used_year1 = getattr(a, 'budget_used_year1', None) or 0
        budget_used_year2 = getattr(a, 'budget_used_year2', None) or 0
        budget_used_year3 = getattr(a, 'budget_used_year3', None) or 0
        total_budget_used = budget_used_year1 + budget_used_year2 + budget_used_year3
        calculated_progress = int(round((total_budget_used / budget_total) * 100)) if budget_total > 0 else 0
        
        writer.writerow(
            [
                a.code or "",
                a.initial_activity or "",
                a.proposed_activity or "",
                a.implementing_entity or "",
                a.delivery_partner or "",
                a.results_area or "",
                a.category or "",
                a.budget_year1 or 0,
                a.budget_year2 or 0,
                a.budget_year3 or 0,
                budget_total,
                budget_used_year1,  # Use year1 value for backward compatibility column
                budget_used_year1,
                budget_used_year2,
                budget_used_year3,
                a.status or "",
                calculated_progress,  # Use auto-calculated progress based on all years
                (a.notes or "").replace("\n", " ").replace("\r", " "),
            ]
        )

    from flask import Response

    output.seek(0)
    return Response(
        output.read(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=activities.csv",
        },
    )


@activity_bp.route("/indicators", methods=["GET"])
@login_required
def indicators_list():
    """View all indicators linked to activities."""
    # Simple read-only view of all indicators with their activities
    try:
        indicators = (
            db.session.query(Indicator)
            .join(Activity, Indicator.activity_id == Activity.id)
            .order_by(Activity.code, Indicator.id)
            .all()
        )
    except Exception as e:
        import traceback

        print(f"Error loading indicators: {e}")
        print(traceback.format_exc())
        indicators = []

    return render_template(
        "indicators.html",
        indicators=indicators,
    )


@activity_bp.route("/admin/usage", methods=["GET"])
@admin_required
def usage_statistics():
    """Display user activity and usage statistics (admin only)."""
    from models import UserActivity, User
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Get date range filter
    try:
        days = int(request.args.get("days", "30"))
    except (ValueError, TypeError):
        days = 30
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all activities in the date range
    activities = UserActivity.query.filter(
        UserActivity.timestamp >= start_date
    ).order_by(UserActivity.timestamp.desc()).all()
    
    # Statistics by action
    action_stats = db.session.query(
        UserActivity.action,
        func.count(UserActivity.id).label("count")
    ).filter(
        UserActivity.timestamp >= start_date
    ).group_by(UserActivity.action).all()
    
    # Statistics by user
    user_stats = db.session.query(
        User.username,
        User.email,
        func.count(UserActivity.id).label("activity_count")
    ).join(
        UserActivity, User.id == UserActivity.user_id
    ).filter(
        UserActivity.timestamp >= start_date
    ).group_by(User.id, User.username, User.email).order_by(
        func.count(UserActivity.id).desc()
    ).all()
    
    # Recent activities (last 50)
    recent_activities = UserActivity.query.join(
        User, UserActivity.user_id == User.id
    ).filter(
        UserActivity.timestamp >= start_date
    ).order_by(
        UserActivity.timestamp.desc()
    ).limit(50).all()
    
    # Daily activity count
    # Use database-specific date extraction for compatibility
    # Detect database type and use appropriate date function
    db_url = str(db.engine.url)
    if 'postgresql' in db_url:
        # PostgreSQL: use DATE() function and CAST to text for consistent formatting
        from sqlalchemy import cast, String
        date_expr = func.to_char(func.date(UserActivity.timestamp), 'YYYY-MM-DD')
    else:
        # SQLite: use strftime
        date_expr = func.strftime('%Y-%m-%d', UserActivity.timestamp)
    
    daily_stats_raw = db.session.query(
        date_expr.label("date"),
        func.count(UserActivity.id).label("count")
    ).filter(
        UserActivity.timestamp >= start_date
    ).group_by(
        date_expr
    ).order_by(
        date_expr.desc()
    ).all()
    
    # All dates should now be strings
    daily_stats = [
        (date_val if date_val else 'N/A', count)
        for date_val, count in daily_stats_raw
    ]
    
    return render_template(
        "usage_statistics.html",
        activities=activities,
        action_stats=action_stats,
        user_stats=user_stats,
        recent_activities=recent_activities,
        daily_stats=daily_stats,
        days=days,
        total_activities=len(activities)
    )


