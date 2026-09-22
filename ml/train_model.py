"""
ml/train_model.py
-------------------
Trains the student-performance classification model and saves it to
ml/model/student_performance_model.pkl.

Run this file directly whenever you want to (re)train the model:

    python ml/train_model.py

It is intentionally simple and heavily commented, since this project is
meant to be understandable by a student, not just runnable.

IMPORTANT (educational scope): this model is a decision-support
prototype trained on a small sample dataset. It is NOT a scientifically
validated predictor of a real student's future. It exists to help a
teacher flag students who may need attention -- the teacher always
makes the final call.
"""

import os
import sys
import json

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib

# Allow running this file directly (python ml/train_model.py) as well as
# as part of the package, by making sure the project root is importable.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import Config  # noqa: E402


def load_training_data(csv_path=None):
    """Step 1: Load the CSV dataset."""
    path = csv_path or Config.STUDENTS_CSV
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Training data not found at {path}. "
            "Make sure data/students.csv exists before training."
        )
    df = pd.read_csv(path)
    return df


def clean_data(df):
    """Step 2: Clean the data.

    - Drop rows missing a feature or the target label.
    - Make sure every feature column is numeric.
    """
    required = Config.FEATURE_COLUMNS + ["performance"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Dataset is missing required column(s): {missing_cols}")

    df = df.dropna(subset=required).copy()

    for col in Config.FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=Config.FEATURE_COLUMNS)

    # Keep only rows whose label is one we recognise.
    df = df[df["performance"].isin(Config.PERFORMANCE_ORDER)]

    return df


def select_features(df):
    """Step 3: Select features (X) and target (y)."""
    X = df[Config.FEATURE_COLUMNS].copy()

    # Map text labels ("At Risk"/"Average"/"Good") to the integer
    # classes used internally: 0 = At Risk, 1 = Average, 2 = Good.
    label_to_int = {label: i for i, label in Config.PERFORMANCE_LABELS.items()}
    y = df["performance"].map(label_to_int)

    return X, y


def train_and_evaluate(X, y):
    """Steps 4-6: Split data, train the model, evaluate it."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # RandomForestClassifier is a good default for a small, mixed-scale
    # tabular dataset like this one: it needs little preprocessing and
    # is easy to explain to a non-expert ("many small decision trees
    # vote on the answer").
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=3,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(
        y_test, y_pred,
        target_names=[Config.PERFORMANCE_LABELS[i] for i in sorted(Config.PERFORMANCE_LABELS)],
        zero_division=0,
    )
    matrix = confusion_matrix(y_test, y_pred).tolist()

    print("=" * 60)
    print("EduPredict AI - Model Training Report")
    print("=" * 60)
    print(f"Training rows: {len(X_train)}  |  Test rows: {len(X_test)}")
    print(f"Accuracy on held-out test data: {accuracy:.2%}")
    print("-" * 60)
    print(report)
    print("Confusion matrix (rows = actual, columns = predicted):")
    print(matrix)
    print("=" * 60)

    return model, {
        "accuracy": round(float(accuracy), 4),
        "confusion_matrix": matrix,
        "feature_columns": Config.FEATURE_COLUMNS,
        "class_labels": Config.PERFORMANCE_LABELS,
        "n_train_rows": len(X_train),
        "n_test_rows": len(X_test),
    }


def save_model(model, metadata):
    """Step 7: Save the trained model (and its metadata) using joblib."""
    os.makedirs(Config.MODEL_DIR, exist_ok=True)
    joblib.dump(model, Config.MODEL_PATH)
    with open(Config.MODEL_METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Model saved to: {Config.MODEL_PATH}")
    print(f"Metadata saved to: {Config.MODEL_METADATA_PATH}")


def main():
    print("Loading training data...")
    df = load_training_data()

    print("Cleaning data...")
    df = clean_data(df)
    print(f"Usable rows after cleaning: {len(df)}")

    print("Selecting features and target...")
    X, y = select_features(df)

    print("Training model...")
    model, metadata = train_and_evaluate(X, y)

    print("Saving model...")
    save_model(model, metadata)

    print("\nDone. You can now run the Flask app with: python app.py")


if __name__ == "__main__":
    main()
