"""
utils/data_processor.py
------------------------
Everything related to reading, validating and summarising student data.

There is NO database in this project. "Persistence" simply means reading
from and writing to data/students.csv with pandas. Keeping all of that
logic in one module means app.py stays small and readable.
"""

import os
import hashlib
import pandas as pd

from config import Config


class DataValidationError(Exception):
    """Raised when an uploaded or loaded CSV fails validation."""

    def __init__(self, errors):
        # errors is always a list of human-readable strings so the
        # Flask route can show every problem at once instead of just
        # the first one.
        self.errors = errors if isinstance(errors, list) else [errors]
        super().__init__("; ".join(self.errors))


def load_students(csv_path=None):
    """
    Load the student dataset from disk as a pandas DataFrame.

    Falls back to an empty (but correctly-shaped) DataFrame if the file
    is missing, so pages can show a friendly "no data yet" state instead
    of crashing.
    """
    path = csv_path or Config.STUDENTS_CSV

    if not os.path.exists(path):
        return pd.DataFrame(columns=Config.REQUIRED_COLUMNS + ["performance"])

    df = pd.read_csv(path)
    return df


def validate_dataframe(df):
    """
    Validate a student DataFrame against the required columns and value
    ranges defined in config.py.

    Returns a list of error strings. An empty list means the data is valid.
    This is used both for the default dataset and for teacher CSV uploads.
    """
    errors = []

    missing_columns = [c for c in Config.REQUIRED_COLUMNS if c not in df.columns]
    if missing_columns:
        errors.append(
            "Missing required column(s): " + ", ".join(missing_columns)
        )
        # Can't safely range-check columns that don't exist.
        return errors

    if df.empty:
        errors.append("The file contains no student rows.")
        return errors

    # Required text fields must not be blank.
    for col in ["student_id", "student_name", "class", "division"]:
        if df[col].isnull().any() or (df[col].astype(str).str.strip() == "").any():
            errors.append(f"Column '{col}' has one or more empty values.")

    # Duplicate student IDs would break the /student/<id> lookup.
    if df["student_id"].duplicated().any():
        dupes = df.loc[df["student_id"].duplicated(), "student_id"].unique()
        errors.append(f"Duplicate student_id value(s): {', '.join(map(str, dupes))}")

    # Numeric range checks, using the single source of truth in config.py.
    for col, (low, high) in Config.FIELD_RANGES.items():
        if col not in df.columns:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        if numeric.isnull().any():
            errors.append(f"Column '{col}' has non-numeric or missing value(s).")
            continue
        out_of_range = df.loc[(numeric < low) | (numeric > high), "student_id"]
        if not out_of_range.empty:
            errors.append(
                f"Column '{col}' must be between {low} and {high} "
                f"(check student(s): {', '.join(map(str, out_of_range.tolist()[:5]))}"
                f"{'...' if len(out_of_range) > 5 else ''})"
            )

    return errors


def save_students(df, csv_path=None):
    """Persist the (validated) student DataFrame back to CSV."""
    path = csv_path or Config.STUDENTS_CSV
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def _stable_seed(student_id, salt=""):
    """
    Turn a student_id into a deterministic integer seed. Used so that
    "randomised" per-subject marks and chart figures stay identical
    every time a page is reloaded, instead of jumping around.
    """
    digest = hashlib.md5(f"{student_id}{salt}".encode()).hexdigest()
    return int(digest[:8], 16)


def get_subject_breakdown(row):
    """
    The dataset does not track individual subject marks, but the
    dashboard/analysis pages want a per-subject bar chart. This derives
    plausible, deterministic per-subject marks from the student's
    overall academic figures so the same student always shows the same
    subject chart.
    """
    import random

    base = (
        float(row.get("previous_percentage", 60))
        + float(row.get("internal_marks", 60))
    ) / 2
    rng = random.Random(_stable_seed(row.get("student_id", "0")))
    breakdown = {}
    for subject in Config.SUBJECTS:
        variation = rng.uniform(-8, 8)
        breakdown[subject] = round(max(0, min(100, base + variation)), 1)
    return breakdown


def compute_dashboard_stats(df):
    """
    Compute all the numbers the dashboard cards and charts need, purely
    from the current DataFrame. Nothing here is hard-coded.
    """
    if df.empty:
        return {
            "total_students": 0,
            "at_risk": 0,
            "average": 0,
            "good": 0,
            "average_class_score": 0,
            "performance_distribution": {"At Risk": 0, "Average": 0, "Good": 0},
            "subject_averages": {s: 0 for s in Config.SUBJECTS},
            "attendance_buckets": {},
            "study_hours_vs_performance": {},
        }

    perf_counts = df["performance"].value_counts().to_dict()
    total = len(df)

    numeric_cols = [
        "attendance",
        "previous_percentage",
        "internal_marks",
        "assignment_marks",
        "practical_marks",
    ]
    overall_score = df[numeric_cols].mean(axis=1)
    average_class_score = round(overall_score.mean(), 1)

    # Subject averages, derived the same deterministic way as per-student.
    subject_totals = {s: 0.0 for s in Config.SUBJECTS}
    for _, row in df.iterrows():
        breakdown = get_subject_breakdown(row)
        for s, v in breakdown.items():
            subject_totals[s] += v
    subject_averages = {
        s: round(v / total, 1) for s, v in subject_totals.items()
    }

    # Attendance distribution buckets for the attendance chart.
    bins = [0, 60, 75, 90, 100.01]
    labels = ["Below 60%", "60-75%", "75-90%", "90-100%"]
    attendance_bucketed = pd.cut(
        df["attendance"], bins=bins, labels=labels, right=False
    )
    attendance_buckets = attendance_bucketed.value_counts().reindex(labels).fillna(0).astype(int).to_dict()

    # Study hours vs performance: average study hours per performance band.
    study_vs_perf = (
        df.groupby("performance")["study_hours"]
        .mean()
        .round(1)
        .reindex(Config.PERFORMANCE_ORDER)
        .fillna(0)
        .to_dict()
    )

    return {
        "total_students": total,
        "at_risk": int(perf_counts.get("At Risk", 0)),
        "average": int(perf_counts.get("Average", 0)),
        "good": int(perf_counts.get("Good", 0)),
        "average_class_score": average_class_score,
        "performance_distribution": {
            "At Risk": int(perf_counts.get("At Risk", 0)),
            "Average": int(perf_counts.get("Average", 0)),
            "Good": int(perf_counts.get("Good", 0)),
        },
        "subject_averages": subject_averages,
        "attendance_buckets": attendance_buckets,
        "study_hours_vs_performance": study_vs_perf,
    }


def filter_students(df, search=None, performance=None, risk_level=None,
                     attendance_min=None, marks_min=None, marks_max=None):
    """Apply the students-page search box and filters to the DataFrame."""
    result = df.copy()

    if search:
        search = search.strip().lower()
        result = result[
            result["student_name"].str.lower().str.contains(search, na=False)
            | result["student_id"].astype(str).str.lower().str.contains(search, na=False)
        ]

    if performance and performance != "all":
        result = result[result["performance"] == performance]

    if risk_level and risk_level != "all" and "risk_level" in result.columns:
        result = result[result["risk_level"] == risk_level]

    if attendance_min is not None:
        result = result[result["attendance"] >= float(attendance_min)]

    if marks_min is not None:
        result = result[result["previous_percentage"] >= float(marks_min)]

    if marks_max is not None:
        result = result[result["previous_percentage"] <= float(marks_max)]

    return result


def enrich_with_predictions(df):
    """
    Add live model output to every row: the model's predicted
    performance category, a performance score, its confidence, and the
    rule-based risk score/level from prediction_utils.

    This is what makes the dashboard and student list show CURRENT
    predictions rather than just whatever label happened to be in the
    CSV, which is the whole point of an "AI prediction" dashboard.

    If the model has not been trained yet, prediction columns are
    filled with None so the pages can show a friendly notice instead
    of crashing.
    """
    # Imported here (not at module top) to avoid a circular import,
    # since ml/predict.py also imports from config.py.
    from ml.predict import predict_student, is_model_available
    from utils.prediction_utils import calculate_risk_score, risk_level_from_score

    if df.empty:
        return df.copy()

    model_ready = is_model_available()
    records = []

    for _, row in df.iterrows():
        student = row.to_dict()

        if model_ready:
            try:
                pred = predict_student(student)
            except Exception:
                pred = {
                    "prediction_label": student.get("performance", "Unknown"),
                    "performance_score": None,
                    "confidence": None,
                }
        else:
            pred = {
                "prediction_label": student.get("performance", "Unknown"),
                "performance_score": None,
                "confidence": None,
            }

        risk_score = calculate_risk_score(student)
        risk_level = risk_level_from_score(risk_score)

        student["performance"] = pred.get("prediction_label")
        student["performance_score"] = pred.get("performance_score")
        student["confidence"] = pred.get("confidence")
        student["risk_score"] = risk_score
        student["risk_level"] = risk_level
        records.append(student)

    return pd.DataFrame(records)


def allowed_upload_file(filename):
    """Check a filename has an allowed extension for CSV upload."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_UPLOAD_EXTENSIONS
    )
