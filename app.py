"""
app.py
-------
Main Flask application for EduPredict AI.

This file wires together routes (URLs) with the helper modules in
utils/ and ml/. It intentionally contains very little "logic" of its
own -- data handling lives in utils/data_processor.py, risk/recommendation
logic lives in utils/prediction_utils.py, and the ML model lives in
ml/predict.py. Keeping app.py thin makes it much easier to read.

Run with:
    python app.py
"""

import io
import os
import csv
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, Response, jsonify
)

from config import Config
from utils.data_processor import (
    load_students, save_students, validate_dataframe, DataValidationError,
    compute_dashboard_stats, filter_students, enrich_with_predictions,
    get_subject_breakdown, allowed_upload_file,
)
from utils.prediction_utils import (
    calculate_risk_score, risk_level_from_score, get_strengths,
    get_concerns, get_recommendations,
)
from ml.predict import predict_student, is_model_available, ModelNotTrainedError

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.DATA_DIR, exist_ok=True)


# ---------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------

def login_required(view_func):
    """Simple session-based login guard used on every protected page.

    This is intentionally basic (see README "Limitations"): it is a
    demo authentication system suitable for a local college project,
    not a production-grade security implementation.
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_globals():
    """Values every template can use without each route passing them
    manually (current teacher name, whether the model is trained)."""
    return {
        "teacher_name": session.get("teacher_name"),
        "model_ready": is_model_available(),
    }


# ---------------------------------------------------------------------
# Login / logout
# ---------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Only Keya Yekhe can log in
        if username == "keyayekhe" and password == "keya#123":
            session["logged_in"] = True
            session["teacher_name"] = "Keya Yekhe"
            flash("Welcome back, Keya!", "success")
            return redirect(url_for("dashboard"))

        flash("Incorrect username or password. Please try again.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    df = load_students()
    enriched = enrich_with_predictions(df)
    stats = compute_dashboard_stats(enriched)

    top_risk = []

    if not enriched.empty:
        top_risk = (
            enriched.sort_values("risk_score", ascending=False)
            .head(5)
            .to_dict(orient="records")
        )

    return render_template(
        "dashboard.html",
        stats=stats,
        subjects=Config.SUBJECTS,
        top_risk=top_risk,
        has_data=not df.empty,
    )


# ---------------------------------------------------------------------
# Student management
# ---------------------------------------------------------------------

@app.route("/students")
@login_required
def students():
    df = load_students()
    enriched = enrich_with_predictions(df)

    search = request.args.get("search", "").strip()
    performance = request.args.get("performance", "all")
    risk_level = request.args.get("risk_level", "all")
    attendance_min = request.args.get("attendance_min") or None
    marks_min = request.args.get("marks_min") or None
    marks_max = request.args.get("marks_max") or None

    filtered = filter_students(
        enriched,
        search=search or None,
        performance=performance,
        risk_level=risk_level,
        attendance_min=attendance_min,
        marks_min=marks_min,
        marks_max=marks_max,
    )

    return render_template(
        "students.html",
        students=filtered.to_dict(orient="records"),
        total_count=len(enriched),
        filtered_count=len(filtered),
        search=search,
        performance=performance,
        risk_level=risk_level,
        attendance_min=attendance_min or "",
        marks_min=marks_min or "",
        marks_max=marks_max or "",
        has_data=not df.empty,
    )


@app.route("/student/<student_id>")
@login_required
def student_details(student_id):
    df = load_students()
    match = df[df["student_id"].astype(str) == str(student_id)]

    if match.empty:
        flash(f"No student found with ID '{student_id}'.", "danger")
        return redirect(url_for("students"))

    student = match.iloc[0].to_dict()

    prediction = None

    if is_model_available():
        try:
            prediction = predict_student(student)
        except (ModelNotTrainedError, ValueError):
            prediction = None

    risk_score = calculate_risk_score(student)
    risk_level = risk_level_from_score(risk_score)

    prediction_label = (
        prediction["prediction_label"]
        if prediction
        else student.get("performance", "Unknown")
    )

    context = {
        "student": student,
        "prediction": prediction,
        "prediction_label": prediction_label,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "strengths": get_strengths(student),
        "concerns": get_concerns(student),
        "recommendations": get_recommendations(student, prediction_label),
        "subject_breakdown": get_subject_breakdown(student),
    }

    return render_template("student_details.html", **context)


# ---------------------------------------------------------------------
# Prediction (manual entry form)
# ---------------------------------------------------------------------

@app.route("/prediction", methods=["GET", "POST"])
@login_required
def prediction():
    result = None
    form_data = {}

    if request.method == "POST":
        form_data = request.form.to_dict()
        errors = []

        # Basic info (not used by the model, but shown with the result).
        student_name = form_data.get("student_name", "").strip()
        student_id = form_data.get("student_id", "").strip()
        student_class = form_data.get("student_class", "12th").strip()
        division = form_data.get("division", "").strip()

        if not student_name:
            errors.append("Student name is required.")

        # Validate and collect numeric fields using the same ranges the
        # rest of the app uses, so the form can never silently accept
        # a value the model wasn't trained to expect.
        numeric_values = {}

        for field in Config.FEATURE_COLUMNS:
            raw = form_data.get(field, "")

            try:
                value = float(raw)

            except (TypeError, ValueError):
                errors.append(
                    f"'{field.replace('_', ' ').title()}' must be a number."
                )
                continue

            low, high = Config.FIELD_RANGES[field]

            if value < low or value > high:
                errors.append(
                    f"'{field.replace('_', ' ').title()}' "
                    f"must be between {low} and {high}."
                )
                continue

            numeric_values[field] = value

        if not errors and not is_model_available():
            errors.append(
                "The prediction model hasn't been trained yet. "
                "Run 'python ml/train_model.py' first, then try again."
            )

        if errors:
            for e in errors:
                flash(e, "danger")

        else:
            student_record = {
                "student_id": student_id or "TEMP",
                "student_name": student_name,
                "class": student_class,
                "division": division,
                **numeric_values,
            }

            try:
                model_result = predict_student(numeric_values)

            except (ModelNotTrainedError, ValueError) as e:
                flash(str(e), "danger")

            else:
                risk_score = calculate_risk_score(student_record)
                risk_level = risk_level_from_score(risk_score)

                result = {
                    "student_name": student_name,
                    "student_id": student_id or "—",
                    "student_class": student_class,
                    "division": division or "—",
                    "prediction_label": model_result["prediction_label"],
                    "performance_score": model_result["performance_score"],
                    "confidence": model_result["confidence"],
                    "probabilities": model_result["probabilities"],
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "strengths": get_strengths(student_record),
                    "concerns": get_concerns(student_record),
                    "recommendations": get_recommendations(
                        student_record,
                        model_result["prediction_label"]
                    ),
                }

    return render_template(
        "prediction.html",
        result=result,
        form_data=form_data,
        field_ranges=Config.FIELD_RANGES,
    )


# ---------------------------------------------------------------------
# Class-wide analysis
# ---------------------------------------------------------------------

@app.route("/analysis")
@login_required
def analysis():
    df = load_students()
    enriched = enrich_with_predictions(df)
    stats = compute_dashboard_stats(enriched)

    averages = {}

    if not enriched.empty:
        averages = {
            "attendance": round(enriched["attendance"].mean(), 1),
            "previous_percentage": round(
                enriched["previous_percentage"].mean(), 1
            ),
            "internal_marks": round(
                enriched["internal_marks"].mean(), 1
            ),
            "assignment_marks": round(
                enriched["assignment_marks"].mean(), 1
            ),
            "practical_marks": round(
                enriched["practical_marks"].mean(), 1
            ),
            "study_hours": round(
                enriched["study_hours"].mean(), 1
            ),
        }

    risk_distribution = (
        enriched["risk_level"].value_counts().to_dict()
        if not enriched.empty
        else {}
    )

    return render_template(
        "analysis.html",
        stats=stats,
        averages=averages,
        risk_distribution=risk_distribution,
        subjects=Config.SUBJECTS,
        has_data=not df.empty,
    )


# ---------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------

@app.route("/reports")
@login_required
def reports():
    df = load_students()
    enriched = enrich_with_predictions(df)
    stats = compute_dashboard_stats(enriched)

    if not enriched.empty:
        needs_attention = enriched[
            (enriched["performance"] == "At Risk")
            | (enriched["risk_level"].isin(["Medium Risk", "High Risk"]))
            | (enriched["attendance"] < 65)
            | (enriched["previous_percentage"] < 50)
        ].sort_values("risk_score", ascending=False)

    else:
        needs_attention = enriched

    return render_template(
        "reports.html",
        stats=stats,
        needs_attention=needs_attention.to_dict(orient="records"),
        has_data=not df.empty,
    )


@app.route("/reports/export")
@login_required
def export_report():
    """Export the 'students requiring attention' table as a downloadable CSV."""
    df = load_students()
    enriched = enrich_with_predictions(df)

    if enriched.empty:
        flash("There is no data to export yet.", "warning")
        return redirect(url_for("reports"))

    needs_attention = enriched[
        (enriched["performance"] == "At Risk")
        | (enriched["risk_level"].isin(["Medium Risk", "High Risk"]))
    ].sort_values("risk_score", ascending=False)

    columns = [
        "student_id",
        "student_name",
        "class",
        "division",
        "attendance",
        "previous_percentage",
        "performance",
        "performance_score",
        "risk_score",
        "risk_level",
    ]

    columns = [
        c for c in columns
        if c in needs_attention.columns
    ]

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(columns)

    for _, row in needs_attention.iterrows():
        writer.writerow([
            row.get(c, "")
            for c in columns
        ])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                "attachment; filename=students_requiring_attention.csv"
        },
    )


# ---------------------------------------------------------------------
# CSV upload
# ---------------------------------------------------------------------

@app.route("/upload", methods=["POST"])
@login_required
def upload_csv():
    file = request.files.get("csv_file")

    if file is None or file.filename == "":
        flash("Please choose a CSV file to upload.", "danger")
        return redirect(url_for("students"))

    if not allowed_upload_file(file.filename):
        flash("Only .csv files are supported.", "danger")
        return redirect(url_for("students"))

    try:
        import pandas as pd
        df = pd.read_csv(file)

    except Exception:
        flash(
            "Could not read that file. "
            "Please make sure it is a valid CSV.",
            "danger"
        )
        return redirect(url_for("students"))

    errors = validate_dataframe(df)

    if errors:
        for e in errors:
            flash(e, "danger")

        flash(
            "Upload rejected — please fix the issues above and try again.",
            "warning"
        )

        return redirect(url_for("students"))

    # A valid upload becomes the app's active working dataset.
    if "performance" not in df.columns:
        df["performance"] = "Average"

    save_students(df)

    flash(
        f"Successfully uploaded {len(df)} student record(s). "
        "Dashboard updated.",
        "success"
    )

    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------
# About
# ---------------------------------------------------------------------

@app.route("/about")
@login_required
def about():
    return render_template("about.html")


# ---------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------

@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "404.html",
        error_code=404,
        error_title="Page not found",
        error_message=(
            "The page you're looking for doesn't exist "
            "or may have moved."
        ),
    ), 404


@app.errorhandler(500)
def server_error(_error):
    return render_template(
        "404.html",
        error_code=500,
        error_title="Something went wrong",
        error_message="An unexpected error occurred.",
    ), 500


if __name__ == "__main__":
    # debug=True is convenient for local development and coursework,
    # but should never be enabled in a real production deployment.
    app.run(debug=True, port=5000)