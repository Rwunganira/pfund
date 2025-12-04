from collections import defaultdict

from flask import Blueprint, flash, redirect, render_template, request, url_for, session
import tempfile

import pandas as pd

from auth_routes import admin_required, login_required, ADMIN_EMAIL
from models import Activity, Challenge, db


activity_bp = Blueprint("activity", __name__)


@activity_bp.route("/test")
def test():
    """Minimal test route to check if app is working."""
    return "App is working!"


@activity_bp.route("/")
@login_required
def index():
    """Simplified index route with maximum error handling."""
    # Start with absolute minimal setup
    try:
        # Try to get activities - if this fails, use empty list
        try:
            activities = Activity.query.order_by(Activity.code).all()
        except Exception as db_error:
            import traceback
            print(f"Database error: {db_error}")
            print(traceback.format_exc())
            activities = []
        
        # Get filters
        status_filter = request.args.get("status", "") or ""
        entity_filter = request.args.get("implementing_entity", "") or ""
        category_filter = request.args.get("category", "") or ""
        results_filter = request.args.get("results_area", "") or ""

        # Apply filters if provided
        try:
            if status_filter:
                activities = [a for a in activities if getattr(a, "status", None) == status_filter]
            if entity_filter:
                activities = [a for a in activities if getattr(a, "implementing_entity", None) == entity_filter]
            if category_filter:
                activities = [a for a in activities if getattr(a, "category", None) == category_filter]
            if results_filter:
                activities = [a for a in activities if getattr(a, "results_area", None) == results_filter]
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

    # Summary metrics computed in Python (using stored progress field)
    try:
        total_activities = len(activities) if activities else 0
        total_budget = sum((a.budget_total or 0) for a in activities) if activities else 0
        total_used = sum((a.budget_used or 0) for a in activities) if activities else 0
        avg_progress = (
            sum((a.progress or 0) for a in activities) / total_activities
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
        summary = {"total_activities": 0, "total_budget": 0, "total_used": 0, "avg_progress": 0}

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
        # Attach a computed execution percentage to each activity
        for a in activities or []:
            try:
                total = getattr(a, "budget_total", None) or 0
                used = getattr(a, "budget_used", None) or 0
                a.exec_pct = round((used / total) * 100) if total > 0 else 0
            except Exception:
                a.exec_pct = 0

        total_activities = len(activities) if activities else 0
        total_budget = sum((getattr(a, "budget_total", None) or 0) for a in activities) if activities else 0
        total_used = sum((getattr(a, "budget_used", None) or 0) for a in activities) if activities else 0
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
        summary = {"total_activities": 0, "total_budget": 0, "total_used": 0, "avg_progress": 0}

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

    # Load challenges for the challenges table
    try:
        challenges = Challenge.query.order_by(Challenge.id.desc()).all()
    except Exception as e:
        import traceback
        print(f"Error loading challenges: {e}")
        print(traceback.format_exc())
        challenges = []

    # Render template with all variables
    try:
        return render_template(
            "index.html",
            activities=activities or [],
            activities_with_urls=activities_with_urls or [],
            activity_urls=activity_urls or {},
            summary=summary,
            status_rows=status_rows or [],
            status_filter=status_filter or "",
            entity_filter=entity_filter or "",
            category_filter=category_filter or "",
            results_filter=results_filter or "",
            entities=entities or [],
            categories=categories or [],
            results_areas=results_areas or [],
            challenges=challenges or [],
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
            "budget_used": request.form.get("budget_used") or 0,
            "status": request.form.get("status") or "Planned",
            "progress": request.form.get("progress") or 0,
            "notes": request.form.get("notes") or None,
        }

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
            budget_total=float(data["budget_total"] or 0),
            budget_used=float(data["budget_used"] or 0),
            status=data["status"],
            progress=int(data["progress"] or 0),
            notes=data["notes"],
        )
        db.session.add(activity)
        db.session.commit()
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
            "budget_used": request.form.get("budget_used") or 0,
            "status": request.form.get("status") or "Planned",
            "progress": request.form.get("progress") or 0,
            "notes": request.form.get("notes") or None,
        }

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
        activity.budget_used = float(data["budget_used"] or 0)
        activity.status = data["status"]
        activity.progress = int(data["progress"] or 0)
        activity.notes = data["notes"]

        db.session.commit()
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

            budget_year1 = get_num(row, "Sum of adjusted_bdg_year1", "Budget Y1")
            budget_year2 = get_num(row, "Sum of adjusted_bdg_year2", "Budget Y2")
            budget_year3 = get_num(row, "Sum of adjusted_bdg_year3", "Budget Y3")
            budget_total = get_num(row, "Sum of TOTAL", "Total Budget")
            budget_used = get_num(row, "Budget used", "Budget Used")

            # Default status and progress for imported rows
            status = "Planned"
            progress = 0

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
                    budget_used,
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
                    budget_used,
                    status,
                    progress,
                    notes,
                ) = row

                existing = None
                if code:
                    existing = Activity.query.filter_by(code=code).first()
                if existing:
                    # Update existing record
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
                    existing.budget_used = budget_used
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
                        budget_used=budget_used,
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
    status_filter = request.args.get("status", "")
    entity_filter = request.args.get("implementing_entity", "")

    query = Activity.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if entity_filter:
        query = query.filter_by(implementing_entity=entity_filter)

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
            "budget_used",
            "status",
            "progress",
            "notes",
        ]
    )
    for a in activities:
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
                a.budget_total or 0,
                a.budget_used or 0,
                a.status or "",
                a.progress or 0,
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


