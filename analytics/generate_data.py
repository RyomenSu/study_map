"""
Generates synthetic data: 14 regions, ~35 schools, 500 students,
3 months of submissions across 4 subjects.
Run once: python generate_data.py
"""
import random
import json
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

DB_URL = "postgresql://postgres:postgres@localhost:5432/analytics"

REGIONS = [
    "Tashkent", "Samarkand", "Fergana", "Andijan", "Namangan",
    "Bukhara", "Kashkadarya", "Surkhandarya", "Jizzakh", "Sirdarya",
    "Khorezm", "Navoi", "Karakalpakstan", "Tashkent Region"
]
SUBJECTS = ["math", "physics", "chemistry", "biology"]
WEAK_TOPICS = {
    "math": ["algebra", "geometry", "trigonometry", "calculus", "statistics"],
    "physics": ["mechanics", "thermodynamics", "electromagnetism", "optics", "quantum"],
    "chemistry": ["organic", "inorganic", "electrochemistry", "kinetics", "equilibrium"],
    "biology": ["genetics", "ecology", "cell_biology", "evolution", "physiology"],
}

def make_score_series(pattern: str, n: int = 3) -> list[float]:
    """weak: 45→42→38, medium: 65→63→70, strong: 80→85→88"""
    if pattern == "weak":
        base = random.uniform(38, 50)
        return [round(base - i * random.uniform(1, 4) + random.gauss(0, 2), 1) for i in range(n)]
    elif pattern == "medium":
        base = random.uniform(60, 72)
        deltas = [-2, -1, 5]
        return [round(base + deltas[i] + random.gauss(0, 3), 1) for i in range(n)]
    else:  # strong
        base = random.uniform(78, 85)
        return [round(base + i * random.uniform(2, 4) + random.gauss(0, 2), 1) for i in range(n)]

def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))

def score_to_level(s):
    if s >= 80: return "high"
    if s >= 55: return "medium"
    return "low"

def score_to_risk(s):
    if s >= 75: return "low"
    if s >= 50: return "medium"
    return "high"

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Clean slate
cur.execute("TRUNCATE submissions, predictions, recommendations, students, schools, regions RESTART IDENTITY CASCADE;")
conn.commit()


# Regions
cur.executemany("INSERT INTO regions (name) VALUES (%s) ON CONFLICT DO NOTHING", [(r,) for r in REGIONS])
conn.commit()
cur.execute("SELECT id, name FROM regions")
region_map = {name: rid for rid, name in cur.fetchall()}

# Schools: 2-3 per region
schools = []
for rname, rid in region_map.items():
    for i in range(random.randint(2, 3)):
        schools.append((rid, f"{rname} School #{i+1}"))
execute_values(cur, "INSERT INTO schools (region_id, name) VALUES %s RETURNING id", schools)
school_ids = [row[0] for row in cur.fetchall()]
conn.commit()

# Students: 500 total
patterns = ["weak"] * 150 + ["medium"] * 200 + ["strong"] * 150
random.shuffle(patterns)
student_rows = []
for i in range(500):
    school_id = random.choice(school_ids)
    grade = random.randint(8, 11)
    student_rows.append((school_id, f"Student_{i+1}", grade))
execute_values(cur, "INSERT INTO students (school_id, name, grade) VALUES %s RETURNING id", student_rows)
student_ids = [row[0] for row in cur.fetchall()]
conn.commit()

# Submissions: 3 months × 4 subjects per student
base_date = datetime.now() - timedelta(days=90)
submission_rows = []
for idx, sid in enumerate(student_ids):
    pattern = patterns[idx]
    for subj in SUBJECTS:
        scores = make_score_series(pattern)
        for month_i, score in enumerate(scores):
            score = clamp(score)
            topics = WEAK_TOPICS[subj]
            weak = random.sample(topics, k=random.randint(1, 3)) if score < 70 else []
            strong = random.sample(topics, k=random.randint(1, 2)) if score >= 60 else []
            error_types = {"conceptual": random.randint(0, 3), "calculation": random.randint(0, 5)}
            created_at = base_date + timedelta(days=month_i * 30 + random.randint(0, 5))
            submission_rows.append((
                sid, subj, round(score, 1),
                score_to_level(score), score_to_risk(score),
                json.dumps(weak), json.dumps(strong), json.dumps(error_types),
                created_at, f"assign_{idx}_{subj}_{month_i}"
            ))

execute_values(cur, """
    INSERT INTO submissions
        (student_id, subject, total_score, understanding_level, exam_risk,
         weak_topics, strong_topics, error_types, created_at, assignment_id)
    VALUES %s
""", submission_rows)
conn.commit()
cur.close()
conn.close()
print(f"Done: {len(submission_rows)} submissions, {len(student_ids)} students, {len(school_ids)} schools")
