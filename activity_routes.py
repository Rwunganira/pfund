from collections import defaultdict

from flask import Blueprint, flash, redirect, render_template, request, url_for, session
import tempfile

import pandas as pd

from auth_routes import admin_required, login_required, ADMIN_EMAIL
from models import Activity, db


activity_bp = Blueprint("activity", __name__)


@activity_bp.route("/")
@login_required
def index():
    status_filter = request.args.get("status", "")
    entity_filter = request.args.get("implementing_entity", "")

    # Build query with filters
    query = Activity.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if entity_filter:
        query = query.filter_by(implementing_entity=entity_filter)

    activities = query.order_by(Activity.code).all()

    # Summary metrics computed in Python
    total_activities = len(activities)
    total_budget = sum(a.budget_total or 0 for a in activities)
    total_used = sum(a.budget_used or 0 for a in activities)
    avg_progress = (
        sum(a.progress or 0 for a in activities) / total_activities
        if total_activities
        else 0
    )
    summary = {
        "total_activities": total_activities,
        "total_budget": total_budget,
        "total_used": total_used,
        "avg_progress": avg_progress,
    }

    # Breakdown by status
    by_status = defaultdict(lambda: {"count": 0, "budget": 0.0})
    for a in activities:
        key = a.status or "Unknown"
        by_status[key]["count"] += 1
        by_status[key]["budget"] += a.budget_total or 0

    status_rows = [
        {"status": status, "count": data["count"], "budget": data["budget"]}
        for status, data in sorted(by_status.items())
    ]

    # For filter dropdowns (distinct implementing_entity)
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

    return render_template(
        "index.html",
        activities=activities,
        summary=summary,
        status_rows=status_rows,
        status_filter=status_filter,
        entity_filter=entity_filter,
        entities=entities,
    )


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
        return redirect(url_for("activity.index"))

    return render_template("form.html", activity=activity)


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


