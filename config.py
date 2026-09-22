"""
config.py
---------
Central place for all EduPredict AI settings.

Nothing in this project talks to a database. Login credentials, risk
thresholds and file locations all live here so a teacher (or a student
extending this project) can tweak behaviour without touching app logic.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Flask needs a secret key to sign session cookies. In a real
    # production app this MUST come from an environment variable and
    # never be committed to source control. For this local/college
    # project a fixed fallback is fine.
    SECRET_KEY = os.environ.get("EDUPREDICT_SECRET_KEY", "edupredict-dev-secret-key")

    # ---- Demo authentication -------------------------------------------
    # There is no database, so the demo teacher account lives right here.
    # Change these two values to change the login credentials.
    DEMO_USERNAME = "teacher"
    DEMO_PASSWORD = "teacher123"
    DEMO_DISPLAY_NAME = "Mrs. Patil"

    # ---- File locations --------------------------------------------------
    DATA_DIR = os.path.join(BASE_DIR, "data")
    STUDENTS_CSV = os.path.join(DATA_DIR, "students.csv")
    SAMPLE_CSV = os.path.join(DATA_DIR, "sample_students.csv")

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    ALLOWED_UPLOAD_EXTENSIONS = {"csv"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB upload limit

    MODEL_DIR = os.path.join(BASE_DIR, "ml", "model")
    MODEL_PATH = os.path.join(MODEL_DIR, "student_performance_model.pkl")
    MODEL_METADATA_PATH = os.path.join(MODEL_DIR, "model_metadata.json")

    # ---- Required columns for any CSV (uploaded or default) --------------
    REQUIRED_COLUMNS = [
        "student_id",
        "student_name",
        "class",
        "division",
        "attendance",
        "previous_percentage",
        "internal_marks",
        "assignment_marks",
        "practical_marks",
        "study_hours",
        "class_participation",
        "homework_completion",
        "previous_backlogs",
        "previous_test_score",
    ]

    # Columns the ML model is trained on, in a fixed order. Both
    # ml/train_model.py and ml/predict.py import this list so the
    # training features and prediction features can never drift apart.
    FEATURE_COLUMNS = [
        "attendance",
        "previous_percentage",
        "internal_marks",
        "assignment_marks",
        "practical_marks",
        "study_hours",
        "class_participation",
        "homework_completion",
        "previous_backlogs",
        "previous_test_score",
    ]

    # Human-readable valid range for each numeric field, used by both
    # the upload validator and the prediction form validator.
    FIELD_RANGES = {
        "attendance": (0, 100),
        "previous_percentage": (0, 100),
        "internal_marks": (0, 100),
        "assignment_marks": (0, 100),
        "practical_marks": (0, 100),
        "study_hours": (0, 24),
        "class_participation": (0, 10),
        "homework_completion": (0, 100),
        "previous_backlogs": (0, 20),
        "previous_test_score": (0, 100),
    }

    # ---- Prediction labels -------------------------------------------
    PERFORMANCE_LABELS = {0: "At Risk", 1: "Average", 2: "Good"}
    PERFORMANCE_ORDER = ["At Risk", "Average", "Good"]

    # ---- Risk score thresholds (0-100, higher = more risk) -----------
    # Kept configurable here rather than buried in application logic.
    RISK_LOW_MAX = 30      # 0-30   -> Low Risk
    RISK_MEDIUM_MAX = 60   # 31-60  -> Medium Risk
    # anything above RISK_MEDIUM_MAX -> High Risk

    # Subjects shown on the "average marks by subject" dashboard chart.
    # These are illustrative and randomly derived from each student's
    # overall marks (the dataset does not track per-subject scores).
    SUBJECTS = ["Physics", "Chemistry", "Mathematics", "Biology", "English", "Computer Science"]
