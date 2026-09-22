"""
ml/predict.py
--------------
Loads the trained model (once) and turns a single student's data into
a prediction the rest of the app can use.

Kept deliberately separate from train_model.py: training happens rarely
and offline, prediction happens on every request, so they have
different jobs and different error-handling needs.
"""

import os
import sys

import joblib
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config  # noqa: E402


class ModelNotTrainedError(Exception):
    """Raised when a prediction is requested but no trained model exists yet."""
    pass


_model_cache = None


def _load_model():
    """Load the trained model from disk, caching it in memory so we do
    not re-read the pickle file on every single prediction request."""
    global _model_cache

    if _model_cache is not None:
        return _model_cache

    if not os.path.exists(Config.MODEL_PATH):
        raise ModelNotTrainedError(
            "No trained model was found. Run 'python ml/train_model.py' "
            "first to train and save the model."
        )

    _model_cache = joblib.load(Config.MODEL_PATH)
    return _model_cache


def preprocess_student(student_data):
    """
    Step: Preprocess incoming student data into the exact feature
    order the model was trained on.

    student_data: dict-like with the FEATURE_COLUMNS keys (values may
    arrive as strings from an HTML form, so they are cast to float).
    """
    row = {}
    for col in Config.FEATURE_COLUMNS:
        if col not in student_data:
            raise ValueError(f"Missing required field for prediction: '{col}'")
        try:
            row[col] = float(student_data[col])
        except (TypeError, ValueError):
            raise ValueError(f"Field '{col}' must be a number.")

    return pd.DataFrame([row], columns=Config.FEATURE_COLUMNS)


def predict_student(student_data):
    """
    Run a prediction for a single student.

    Returns a dict with:
      - prediction_class: int (0/1/2)
      - prediction_label: str ("At Risk"/"Average"/"Good")
      - confidence: float 0-1, the model's probability for the
        predicted class
      - probabilities: dict label -> probability, for all three classes
      - performance_score: float 0-100, a friendly "percentage" version
        derived from the class probabilities (see note below)
    """
    model = _load_model()
    X = preprocess_student(student_data)

    prediction_class = int(model.predict(X)[0])
    proba = model.predict_proba(X)[0]

    probabilities = {
        Config.PERFORMANCE_LABELS[i]: round(float(p), 4)
        for i, p in enumerate(proba)
    }
    confidence = round(float(proba[prediction_class]), 4)

    # A single "performance score" out of 100 is easier for a teacher
    # to scan than three separate probabilities. We derive it as a
    # weighted blend of the class probabilities (At Risk=0, Average=50,
    # Good=100), NOT as a claim of precise academic measurement.
    class_score_anchor = {0: 0, 1: 50, 2: 100}
    performance_score = round(
        float(sum(proba[i] * class_score_anchor[i] for i in range(len(proba)))), 1
    )

    return {
        "prediction_class": prediction_class,
        "prediction_label": Config.PERFORMANCE_LABELS[prediction_class],
        "confidence": confidence,
        "probabilities": probabilities,
        "performance_score": performance_score,
    }


def is_model_available():
    """Used by app.py to show a friendly message instead of a crash if
    the teacher hasn't trained the model yet."""
    return os.path.exists(Config.MODEL_PATH)
