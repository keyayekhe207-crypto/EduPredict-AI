"""
utils/prediction_utils.py
---------------------------
Turns a student's raw numbers into the things a teacher actually reads:
a transparent risk score, a risk level, a list of strengths, a list of
areas needing attention, and specific recommendations.

None of this is the ML model itself (that lives in ml/predict.py) -
this module is the rule-based "explanation layer" that sits on top of
the model's category prediction and makes it useful to a teacher.
"""

from config import Config


# Each factor: (field name, weight in the 0-100 risk score, "low is bad" or "high is bad")
RISK_FACTORS = [
    ("attendance", 20, "low"),
    ("previous_percentage", 20, "low"),
    ("study_hours", 12, "low"),
    ("internal_marks", 15, "low"),
    ("assignment_marks", 10, "low"),
    ("practical_marks", 8, "low"),
    ("previous_backlogs", 10, "high"),
    ("class_participation", 5, "low"),
]


def _normalise(value, field):
    """Scale a raw field value to 0-1, where 1 always means 'more risk'."""
    low, high = Config.FIELD_RANGES[field]
    span = (high - low) or 1
    ratio = (float(value) - low) / span
    ratio = max(0.0, min(1.0, ratio))

    direction = next(d for f, w, d in RISK_FACTORS if f == field)
    return (1 - ratio) if direction == "low" else ratio


def calculate_risk_score(student):
    """
    Compute a transparent 0-100 risk score from a student's raw values.
    Higher = more risk. Thresholds for Low/Medium/High risk live in
    config.py so a teacher can retune them without touching this logic.
    """
    total_weight = sum(w for _, w, _ in RISK_FACTORS)
    score = 0.0
    for field, weight, _direction in RISK_FACTORS:
        if field not in student:
            continue
        score += _normalise(student[field], field) * weight

    risk_score = round((score / total_weight) * 100, 1)
    return risk_score


def risk_level_from_score(risk_score):
    if risk_score <= Config.RISK_LOW_MAX:
        return "Low Risk"
    elif risk_score <= Config.RISK_MEDIUM_MAX:
        return "Medium Risk"
    return "High Risk"


# Thresholds used to decide whether a factor is a strength or a concern.
# These are intentionally a bit more forgiving than the risk-score
# weighting above, since "good enough" and "excellent" are different
# messages for a teacher.
_STRENGTH_RULES = {
    "attendance": (85, "Good attendance ({value:.0f}%)"),
    "previous_percentage": (75, "Strong previous exam performance ({value:.0f}%)"),
    "internal_marks": (75, "Strong internal assessment marks ({value:.0f}%)"),
    "assignment_marks": (75, "Consistent, high-quality assignment work ({value:.0f}%)"),
    "practical_marks": (75, "Good practical/lab performance ({value:.0f}%)"),
    "study_hours": (4, "Healthy daily study routine ({value:.1f} hrs/day)"),
    "class_participation": (7, "Actively participates in class ({value:.0f}/10)"),
    "homework_completion": (85, "Reliable homework completion ({value:.0f}%)"),
    "previous_test_score": (75, "Solid recent test scores ({value:.0f}%)"),
}

_CONCERN_RULES = {
    "attendance": (65, "Low attendance ({value:.0f}%) is affecting continuity of learning"),
    "previous_percentage": (50, "Previous examination score ({value:.0f}%) is below class average"),
    "internal_marks": (50, "Internal assessment marks ({value:.0f}%) need improvement"),
    "assignment_marks": (50, "Assignment scores ({value:.0f}%) suggest gaps in practice"),
    "practical_marks": (50, "Practical/lab performance ({value:.0f}%) needs support"),
    "study_hours": (2, "Very limited daily study time ({value:.1f} hrs/day)"),
    "class_participation": (4, "Low class participation ({value:.0f}/10)"),
    "homework_completion": (60, "Inconsistent homework completion ({value:.0f}%)"),
    "previous_test_score": (50, "Recent test scores ({value:.0f}%) are a concern"),
}


def _field_value(student, field):
    try:
        return float(student.get(field, 0))
    except (TypeError, ValueError):
        return 0.0


def get_strengths(student):
    """Return a list of strength strings, generated only from fields
    that actually clear the threshold for THIS student."""
    strengths = []
    for field, (threshold, template) in _STRENGTH_RULES.items():
        value = _field_value(student, field)
        if value >= threshold:
            strengths.append(template.format(value=value))

    backlogs = int(_field_value(student, "previous_backlogs"))
    if backlogs == 0:
        strengths.append("No pending backlogs")

    if not strengths:
        strengths.append(
            "No standout strengths identified yet — worth a direct "
            "conversation to find what motivates this student."
        )
    return strengths


def get_concerns(student):
    """Return a list of areas-needing-attention strings, generated only
    from fields that fall below the threshold for THIS student."""
    concerns = []
    for field, (threshold, template) in _CONCERN_RULES.items():
        value = _field_value(student, field)
        if value < threshold:
            concerns.append(template.format(value=value))

    backlogs = int(_field_value(student, "previous_backlogs"))
    if backlogs >= 2:
        concerns.append(f"{backlogs} pending backlogs from previous terms")
    elif backlogs == 1:
        concerns.append("1 pending backlog from a previous term")

    return concerns


# Recommendation generated per concern, so two students with different
# weak points get different advice rather than a fixed list.
_RECOMMENDATION_MAP = {
    "attendance": "Monitor attendance closely and understand the underlying reason for absences.",
    "previous_percentage": "Review foundational topics from previous exams with the student.",
    "internal_marks": "Provide additional practice tests focused on internal assessment topics.",
    "assignment_marks": "Set shorter, more frequent assignments to rebuild consistency.",
    "practical_marks": "Schedule extra lab/practical sessions or peer-assisted practice.",
    "study_hours": "Help the student build a realistic daily study schedule.",
    "class_participation": "Encourage participation with small, low-pressure discussion prompts.",
    "homework_completion": "Check in on homework more frequently and address any blockers early.",
    "previous_test_score": "Offer targeted revision material for recently tested topics.",
    "previous_backlogs": "Prioritise clearing pending backlogs before introducing new material.",
}


def get_recommendations(student, prediction_label):
    """
    Build a recommendation list tailored to this student's specific weak
    fields. Every recommendation is traceable back to a concern, so no
    two students with different data get identical advice.
    """
    concerns = get_concerns(student)
    recommendations = []

    # Map concerns back to fields by checking which field's template
    # produced each concern string's leading topic — simplest reliable
    # way to keep the mapping in one place is to re-derive it directly.
    for field, (threshold, _template) in _CONCERN_RULES.items():
        value = _field_value(student, field)
        if value < threshold and field in _RECOMMENDATION_MAP:
            recommendations.append(_RECOMMENDATION_MAP[field])

    backlogs = int(_field_value(student, "previous_backlogs"))
    if backlogs >= 1:
        recommendations.append(_RECOMMENDATION_MAP["previous_backlogs"])

    if prediction_label == "At Risk":
        recommendations.append("Schedule a one-to-one discussion with the student and, if appropriate, a parent/guardian.")
    elif prediction_label == "Average":
        recommendations.append("Set a short-term improvement goal and review progress in 2-3 weeks.")
    else:
        recommendations.append("Encourage the student to mentor peers or take on stretch material.")

    # De-duplicate while preserving order.
    seen = set()
    unique_recommendations = []
    for r in recommendations:
        if r not in seen:
            seen.add(r)
            unique_recommendations.append(r)

    return unique_recommendations
