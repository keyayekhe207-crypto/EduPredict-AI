# EduPredict AI

**A local, database-free student performance prediction system for 12th-standard teachers.**

EduPredict AI helps teachers spot students who may need extra academic attention — using attendance, marks, study habits and a few other signals — and turns that into a clear dashboard, a per-student risk breakdown, and specific recommendations.

> ⚠️ **This is an educational decision-support prototype**, built as a college project. It is **not** a scientifically validated predictor of a real student's future performance. It exists to help a teacher notice patterns early — the teacher always makes the final call.

---

## 1. Features

- 🔐 Simple local teacher login (no database, no external auth service)
- 📊 Dashboard with live stats and 4 Chart.js visualisations, computed from your actual data
- 🧑‍🎓 Searchable, filterable student list (by name/ID, performance, risk level, attendance, marks)
- 👤 Individual student profile pages with a transparent risk score
- 🤖 A Random Forest ML model that classifies each student as **At Risk / Average / Good**
- 💡 Per-student strengths, concerns and recommendations — generated from *that student's* own numbers, not a fixed template
- 📈 Class-wide analysis page (5 charts: performance, risk, attendance, subjects, study hours)
- 📄 Reports page with a "students requiring attention" table and one-click CSV export
- 📤 CSV upload to replace the working dataset, with full validation and clear error messages
- 🚫 **No SQL, no database, no external hosting** — everything runs from local CSV files

---

## 2. Technologies

| Layer            | Technology                                 |
|-------------------|---------------------------------------------|
| Backend           | Python 3, Flask                             |
| Machine learning  | scikit-learn (Random Forest), pandas, NumPy |
| Model storage     | joblib (`.pkl`)                             |
| Frontend          | HTML5, CSS3, Bootstrap 5, Bootstrap Icons   |
| Charts            | Chart.js                                    |
| Data storage      | CSV files (no database of any kind)         |

---

## 3. Folder structure

```
EduPredict-AI/
│
├── app.py                     # Main Flask application (routes)
├── config.py                  # Settings: login, thresholds, file paths, feature list
├── requirements.txt
├── README.md
├── .gitignore
│
├── data/
│   ├── students.csv           # Active working dataset used by the app
│   └── sample_students.csv    # Small demo file for testing CSV upload
│
├── ml/
│   ├── train_model.py         # Trains and saves the model
│   ├── predict.py             # Loads the model and runs predictions
│   └── model/
│       ├── student_performance_model.pkl   # created by train_model.py
│       └── model_metadata.json             # created by train_model.py
│
├── utils/
│   ├── data_processor.py      # Load/validate/save CSV, dashboard stats, filtering
│   └── prediction_utils.py    # Risk score, strengths/concerns/recommendations
│
├── static/
│   ├── css/style.css
│   ├── js/dashboard.js
│   ├── js/prediction.js
│   ├── js/charts.js
│   └── images/
│
├── templates/
│   ├── base.html, login.html, dashboard.html, students.html,
│   │   student_details.html, prediction.html, analysis.html,
│   │   reports.html, about.html, 404.html
│
└── uploads/                   # Temporary landing spot for file uploads
```

---

## 4. Installation

You need **Python 3.9+** installed. Check with:

```bash
python --version
```

### Step 1 — Get the files onto your computer

Create the folder structure above and paste each file's code into the matching file, or place all the provided files into a folder named `EduPredict-AI`.

### Step 2 — Create a virtual environment

```bash
cd EduPredict-AI

# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` appear at the start of your terminal prompt.

### Step 3 — Install requirements

```bash
pip install -r requirements.txt
```

---

## 5. Train the model

Before running the app for the first time, train the prediction model:

```bash
python ml/train_model.py
```

This reads `data/students.csv`, trains a Random Forest classifier, prints an accuracy report, and saves the model to `ml/model/student_performance_model.pkl`. Re-run this anytime you significantly change `data/students.csv` and want the model to reflect the new data.

---

## 6. Run the application

```bash
python app.py
```

You should see Flask start a local server, typically at:

```
http://127.0.0.1:5000
```

Open that address in your browser.

---

## 7. Demo login credentials

```
Username: teacher
Password: teacher123
```

Change these anytime in `config.py` (`DEMO_USERNAME` / `DEMO_PASSWORD`).

---

## 8. Using the app

1. **Login** with the demo credentials above.
2. **Dashboard** — see live class stats and charts.
3. **Students** — search, filter, and open individual student profiles. Use the **Upload CSV** button to replace the dataset (try `data/sample_students.csv` first).
4. **Prediction** — manually enter a student's numbers and get an instant prediction, risk score, and recommendations.
5. **Analysis** — class-wide trends across five charts.
6. **Reports** — a focused list of students needing attention, exportable to CSV.

---

## 9. CSV format

Any CSV you upload (or use as `data/students.csv`) must include these columns:

```
student_id, student_name, class, division,
attendance, previous_percentage, internal_marks,
assignment_marks, practical_marks, study_hours,
class_participation, homework_completion,
previous_backlogs, previous_test_score
```

Validation rules:

| Column                  | Valid range |
|--------------------------|-------------|
| attendance                | 0–100      |
| previous_percentage       | 0–100      |
| internal_marks            | 0–100      |
| assignment_marks          | 0–100      |
| practical_marks           | 0–100      |
| study_hours                | 0–24       |
| class_participation        | 0–10       |
| homework_completion        | 0–100      |
| previous_backlogs          | 0–20       |
| previous_test_score        | 0–100      |

`student_id` must be unique. Rows outside these ranges, or with missing required columns, are rejected with a clear on-screen message listing every problem found.

---

## 10. How prediction works

1. `ml/train_model.py` loads `data/students.csv`, cleans it, and trains a `RandomForestClassifier` on 10 numeric features (see `FEATURE_COLUMNS` in `config.py`), predicting **At Risk (0) / Average (1) / Good (2)**.
2. The trained model is saved with `joblib` to `ml/model/student_performance_model.pkl`.
3. `ml/predict.py` loads that file once and reuses it for every prediction, returning a label, a confidence score, and a 0–100 "performance score."
4. Separately, `utils/prediction_utils.py` computes a transparent, rule-based **risk score** (0–100) from the same fields, using configurable weights — so a teacher can see exactly *why* a student was flagged, independent of the ML model's internal reasoning.
5. Strengths, concerns, and recommendations are generated per student by comparing their individual field values against thresholds — two students with different weak points receive different advice.

Risk-level thresholds (configurable in `config.py`):

```
0–30   → Low Risk
31–60  → Medium Risk
61–100 → High Risk
```

---

## 11. Limitations

- Trained on a small, partly-simulated sample dataset — accuracy will vary with real data.
- Not a substitute for a teacher's professional judgement.
- Demo authentication only (single hardcoded account, no password hashing) — **do not** use this login system in a real production setting.
- Per-subject marks shown in charts are illustrative estimates (the dataset does not track individual subjects).
- No automated tests are included.

---

## 12. Future improvements

- Real per-subject mark tracking instead of estimated breakdowns
- Multiple teacher accounts with hashed passwords
- Exportable PDF report cards per student
- Support for tracking a student's performance over multiple terms
- A model comparison mode (Logistic Regression vs. Random Forest vs. others)

---

## 13. Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Make sure your virtual environment is activated, then re-run `pip install -r requirements.txt`. |
| "Prediction model not trained yet" banner | Run `python ml/train_model.py`, then refresh the page. |
| CSV upload rejected | Read the listed errors — usually a missing column or an out-of-range value. |
| Port 5000 already in use | Edit the last line of `app.py` and change `port=5000` to another port, e.g. `port=5050`. |

---

## 14. Optional: regenerating the sample dataset

`generate_sample_data.py` (project root) is the small script used to create the fictional `data/students.csv` and `data/sample_students.csv` shipped with this project. It's not required to run the app — it's included so you can regenerate a fresh, differently-sized dataset if you want to experiment:

```bash
python generate_sample_data.py
```

Re-run `python ml/train_model.py` afterwards so the model reflects the new data.

---

Built as a local college project. No data leaves your computer.
