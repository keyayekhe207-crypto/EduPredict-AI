"""
One-off script to generate a realistic fictional sample_students.csv
for the EduPredict AI project. Not part of the shipped app; run once
to produce data/sample_students.csv and data/students.csv.
"""
import numpy as np
import pandas as pd

np.random.seed(42)

first_names = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krishna",
    "Ishaan", "Rohan", "Kabir", "Dev", "Yash", "Aryan", "Kartik", "Om",
    "Ananya", "Diya", "Saanvi", "Aadhya", "Myra", "Isha", "Riya", "Kavya",
    "Sneha", "Priya", "Neha", "Pooja", "Meera", "Tanvi", "Anika", "Shreya",
    "Rahul", "Aman", "Nikhil", "Varun", "Siddharth", "Karan", "Harsh", "Raj",
    "Pallavi", "Sanya", "Nisha", "Ritika", "Simran", "Divya", "Swati", "Juhi",
]
last_names = [
    "Sharma", "Verma", "Patil", "Kulkarni", "Deshmukh", "Joshi", "Iyer",
    "Reddy", "Nair", "Gupta", "Kumar", "Singh", "Mehta", "Shah", "Chavan",
    "Pawar", "Kale", "Bhosale", "Rane", "Naik", "Rao", "Menon", "Pillai",
]

divisions = ["A", "B", "C"]
class_label = "12th"

n_students = 140
rows = []
used_names = set()

for i in range(1, n_students + 1):
    sid = f"STU{i:04d}"
    while True:
        name = f"{np.random.choice(first_names)} {np.random.choice(last_names)}"
        if name not in used_names:
            used_names.add(name)
            break

    # Latent "ability" score drives correlated features, plus noise,
    # so the dataset has a learnable signal without being deterministic.
    ability = np.clip(np.random.normal(65, 20), 5, 100)

    attendance = np.clip(ability * 0.6 + np.random.normal(25, 12), 35, 100)
    previous_percentage = np.clip(ability + np.random.normal(0, 8), 20, 99)
    internal_marks = np.clip(ability + np.random.normal(0, 10), 10, 100)
    assignment_marks = np.clip(ability + np.random.normal(5, 10), 10, 100)
    practical_marks = np.clip(ability + np.random.normal(3, 9), 15, 100)
    study_hours = np.clip(ability / 100 * 6 + np.random.normal(0, 1.3), 0.5, 9)
    class_participation = np.clip(ability / 10 + np.random.normal(0, 1.8), 1, 10)
    homework_completion = np.clip(ability + np.random.normal(0, 12), 20, 100)
    previous_test_score = np.clip(ability + np.random.normal(0, 9), 15, 100)
    previous_backlogs = np.random.choice(
        [0, 0, 0, 1, 1, 2, 3], p=[0.45, 0.2, 0.1, 0.1, 0.07, 0.05, 0.03]
    )
    # Backlogs pull ability-derived score down a bit for realism.
    ability_adjusted = ability - previous_backlogs * 4

    composite = (
        attendance * 0.15
        + previous_percentage * 0.20
        + internal_marks * 0.15
        + assignment_marks * 0.10
        + practical_marks * 0.10
        + (study_hours / 9 * 100) * 0.10
        + (class_participation / 10 * 100) * 0.05
        + homework_completion * 0.10
        + previous_test_score * 0.10
        - previous_backlogs * 3
    )
    composite = np.clip(composite, 0, 100)

    if composite < 45:
        performance = "At Risk"
    elif composite < 70:
        performance = "Average"
    else:
        performance = "Good"

    rows.append({
        "student_id": sid,
        "student_name": name,
        "class": class_label,
        "division": np.random.choice(divisions),
        "attendance": round(attendance, 1),
        "previous_percentage": round(previous_percentage, 1),
        "internal_marks": round(internal_marks, 1),
        "assignment_marks": round(assignment_marks, 1),
        "practical_marks": round(practical_marks, 1),
        "study_hours": round(study_hours, 1),
        "class_participation": round(class_participation, 1),
        "homework_completion": round(homework_completion, 1),
        "previous_backlogs": int(previous_backlogs),
        "previous_test_score": round(previous_test_score, 1),
        "performance": performance,
    })

df = pd.DataFrame(rows)
df.to_csv("/home/claude/EduPredict-AI/data/students.csv", index=False)

# A smaller, clearly-labelled demo file teachers can use to test CSV upload.
df.sample(25, random_state=7).sort_values("student_id").to_csv(
    "/home/claude/EduPredict-AI/data/sample_students.csv", index=False
)

print(df["performance"].value_counts())
print(df.shape)
