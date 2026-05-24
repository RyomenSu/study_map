"""
Generate synthetic demo data for the Study-Map studyportal schema.

Mirrors the scale of the original generate_data.py:
  - 14 Uzbekistan regions (Russian names matching the map)
  - 2-3 schools per region (~35 schools total)
  - 1 teacher per school
  - ~15 students per school (~500 total) with weak/medium/strong patterns
  - 4 subjects as courses, 3 assignments each (3-month history)
  - Realistic score distributions per student pattern
  - anlt_predictions and anlt_recommendations for the dashboard

Run inside analytics container:
    python generate_demo_data_studyportal.py
Or from host:
    docker compose exec analytics python generate_demo_data_studyportal.py
"""

from __future__ import annotations

import json
import os
import random
import uuid
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import execute_values

# ── Constants ──────────────────────────────────────────────────────────────────

DEMO_PREFIX = "Demo"
# bcrypt hash for password "demo1234"  (pre-computed, no bcrypt dep needed)
DEMO_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TiGc9.sMg5TuKHq4AF9N9UvMbQFW"

REGIONS = [
    "Ташкент",
    "Ташкентская область",
    "Самарканд",
    "Бухара",
    "Фергана",
    "Андижан",
    "Наманган",
    "Кашкадарья",
    "Сурхандарья",
    "Навои",
    "Хорезм",
    "Джизак",
    "Сырдарья",
    "Каракалпакстан",
]

CITIES = {
    "Ташкент": "Ташкент",
    "Ташкентская область": "Нурафшон",
    "Самарканд": "Самарканд",
    "Бухара": "Бухара",
    "Фергана": "Фергана",
    "Андижан": "Андижан",
    "Наманган": "Наманган",
    "Кашкадарья": "Карши",
    "Сурхандарья": "Термез",
    "Навои": "Навои",
    "Хорезм": "Ургенч",
    "Джизак": "Джизак",
    "Сырдарья": "Гулистан",
    "Каракалпакстан": "Нукус",
}

SUBJECTS = ["История", "Математика", "Физика", "Химия"]

FEEDBACK_TEMPLATES = {
    "high":   "Отличная работа! Чёткое понимание материала, аргументы хорошо структурированы.",
    "medium": "Хорошая попытка. Основные концепции поняты, но есть пробелы в деталях.",
    "low":    "Требуется доработка. Рекомендуется повторить ключевые темы и проконсультироваться с учителем.",
}


# ── Score helpers (same logic as original generate_data.py) ───────────────────

def make_score_series(pattern: str, n: int = 3) -> list[float]:
    rng = random
    if pattern == "weak":
        base = rng.uniform(38, 50)
        return [max(0, min(100, base - i * rng.uniform(1, 4) + rng.gauss(0, 2))) for i in range(n)]
    elif pattern == "medium":
        base = rng.uniform(60, 72)
        deltas = [-2, -1, 5]
        return [max(0, min(100, base + deltas[i] + rng.gauss(0, 3))) for i in range(n)]
    else:  # strong
        base = rng.uniform(78, 85)
        return [max(0, min(100, base + i * rng.uniform(2, 4) + rng.gauss(0, 2))) for i in range(n)]


def score_to_level(s: float) -> str:
    if s >= 80: return "high"
    if s >= 55: return "medium"
    return "low"


# ── DB helpers ────────────────────────────────────────────────────────────────

def _pg_url() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql://studyportal:studyportal_pass@localhost:5432/studyportal",
    ).strip()
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://"):]
    return url


def uid() -> str:
    return str(uuid.uuid4())


# ── Cleanup ───────────────────────────────────────────────────────────────────

def _cleanup_demo(cur) -> None:
    print("Cleaning up previous demo data...")

    cur.execute("SELECT id FROM users WHERE email LIKE 'demo.%%@studymap.uz' OR email LIKE 'demo.%%@studymap.local'")
    demo_user_ids = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT id FROM schools WHERE name LIKE %s", (f"{DEMO_PREFIX} %",))
    demo_school_ids = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT id FROM groups WHERE name LIKE %s", (f"{DEMO_PREFIX} %",))
    demo_group_ids = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT id FROM courses WHERE name LIKE %s", (f"{DEMO_PREFIX} %",))
    demo_course_ids = [row[0] for row in cur.fetchall()]

    if demo_course_ids:
        cur.execute("SELECT id FROM assignments WHERE course_id = ANY(%s::uuid[])", (demo_course_ids,))
        demo_assignment_ids = [row[0] for row in cur.fetchall()]
    else:
        demo_assignment_ids = []

    if demo_assignment_ids:
        cur.execute("SELECT id FROM submissions WHERE assignment_id = ANY(%s::uuid[])", (demo_assignment_ids,))
        demo_submission_ids = [row[0] for row in cur.fetchall()]
    else:
        demo_submission_ids = []

    if demo_submission_ids:
        cur.execute("DELETE FROM grades WHERE submission_id = ANY(%s::uuid[])", (demo_submission_ids,))
        cur.execute("DELETE FROM submissions WHERE id = ANY(%s::uuid[])", (demo_submission_ids,))

    if demo_assignment_ids:
        cur.execute("DELETE FROM assignments WHERE id = ANY(%s::uuid[])", (demo_assignment_ids,))

    if demo_course_ids:
        cur.execute("DELETE FROM enrollments WHERE course_id = ANY(%s::uuid[])", (demo_course_ids,))
        cur.execute("DELETE FROM course_groups WHERE course_id = ANY(%s::uuid[])", (demo_course_ids,))
        cur.execute("DELETE FROM attendance_sessions WHERE course_id = ANY(%s::uuid[])", (demo_course_ids,))
        cur.execute("DELETE FROM courses WHERE id = ANY(%s::uuid[])", (demo_course_ids,))

    if demo_group_ids:
        # Unlink ALL users from these groups first (catches old @studymap.local leftovers too)
        cur.execute("UPDATE users SET group_id = NULL WHERE group_id = ANY(%s::uuid[])", (demo_group_ids,))

    if demo_user_ids:
        cur.execute("DELETE FROM attendance_records WHERE student_id = ANY(%s::uuid[])", (demo_user_ids,))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (demo_user_ids,))

    if demo_group_ids:
        cur.execute("DELETE FROM groups WHERE id = ANY(%s::uuid[])", (demo_group_ids,))

    if demo_school_ids:
        cur.execute("DELETE FROM schools WHERE id = ANY(%s::uuid[])", (demo_school_ids,))

    cur.execute("DELETE FROM anlt_predictions WHERE subject LIKE %s", (f"{DEMO_PREFIX} %",))
    cur.execute("DELETE FROM anlt_recommendations WHERE region_name = ANY(%s)", (REGIONS,))
    print("Cleanup done.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    random.seed(42)
    conn = psycopg2.connect(_pg_url())
    conn.autocommit = False
    cur = conn.cursor()

    _cleanup_demo(cur)

    now = datetime.utcnow()
    base_date = now - timedelta(days=90)

    # ── Schools: 2-3 per region ────────────────────────────────────────────────
    school_rows = []
    for region in REGIONS:
        count = random.randint(2, 3)
        for i in range(1, count + 1):
            school_rows.append((uid(), f"{DEMO_PREFIX} {region} Школа #{i}", region, CITIES[region]))

    execute_values(
        cur,
        "INSERT INTO schools (id, name, region, city) VALUES %s",
        [(r[0], r[1], r[2], r[3]) for r in school_rows],
        template="(%s::uuid, %s, %s, %s)",
    )
    school_ids = [r[0] for r in school_rows]
    school_region = {r[0]: r[2] for r in school_rows}
    print(f"Created {len(school_ids)} schools across {len(REGIONS)} regions.")

    # ── Groups: 1 per school ───────────────────────────────────────────────────
    group_rows = [(uid(), f"{DEMO_PREFIX} Группа {school_ids.index(sid) + 1}", sid) for sid in school_ids]
    execute_values(
        cur,
        "INSERT INTO groups (id, name, school_id) VALUES %s",
        group_rows,
        template="(%s::uuid, %s, %s::uuid)",
    )
    school_group = {sid: group_rows[i][0] for i, sid in enumerate(school_ids)}
    print(f"Created {len(group_rows)} groups.")

    # ── Teachers: 1 per school ─────────────────────────────────────────────────
    teacher_rows = []
    school_teacher = {}
    for i, sid in enumerate(school_ids):
        tid = uid()
        teacher_rows.append((
            tid,
            f"demo.teacher.{i+1}@studymap.uz",
            DEMO_PASSWORD_HASH,
            f"{DEMO_PREFIX} Учитель {i+1}",
            sid,
            None,
        ))
        school_teacher[sid] = tid

    execute_values(
        cur,
        """
        INSERT INTO users (id, email, password_hash, full_name, role, school_id, group_id, is_active)
        VALUES %s
        """,
        [(r[0], r[1], r[2], r[3], r[4], r[5], True) for r in teacher_rows],
        template="(%s::uuid, %s, %s, %s, 'teacher', %s::uuid, %s, %s)",
    )
    print(f"Created {len(teacher_rows)} teachers.")

    # ── Students: ~15 per school, weak/medium/strong patterns ─────────────────
    patterns_pool = ["weak"] * 5 + ["medium"] * 6 + ["strong"] * 4  # ~15 per school
    all_students: list[dict] = []
    student_rows = []

    for sid in school_ids:
        school_patterns = patterns_pool[:]
        random.shuffle(school_patterns)
        for j, pattern in enumerate(school_patterns):
            stu_id = uid()
            idx = len(all_students) + 1
            student_rows.append((
                stu_id,
                f"demo.student.{idx}@studymap.uz",
                DEMO_PASSWORD_HASH,
                f"{DEMO_PREFIX} Студент {idx}",
                sid,
                school_group[sid],
            ))
            all_students.append({"id": stu_id, "school_id": sid, "pattern": pattern})

    execute_values(
        cur,
        """
        INSERT INTO users (id, email, password_hash, full_name, role, school_id, group_id, is_active)
        VALUES %s
        """,
        [(r[0], r[1], r[2], r[3], r[4], r[5], True) for r in student_rows],
        template="(%s::uuid, %s, %s, %s, 'student', %s::uuid, %s::uuid, %s)",
    )
    print(f"Created {len(all_students)} students.")

    # ── Courses: 4 subjects per school ────────────────────────────────────────
    course_rows = []
    school_courses: dict[str, list[str]] = {}
    for sid in school_ids:
        tid = school_teacher[sid]
        cids = []
        for subj in SUBJECTS:
            cid = uid()
            course_rows.append((cid, f"{DEMO_PREFIX} {subj}", f"Демо курс {subj}", tid, sid))
            cids.append(cid)
        school_courses[sid] = cids

    execute_values(
        cur,
        "INSERT INTO courses (id, name, description, teacher_id, school_id) VALUES %s",
        course_rows,
        template="(%s::uuid, %s, %s, %s::uuid, %s::uuid)",
    )
    print(f"Created {len(course_rows)} courses.")

    # ── Link groups to courses + enroll students ───────────────────────────────
    course_group_rows = []
    enroll_rows = []
    for sid in school_ids:
        gid = school_group[sid]
        for cid in school_courses[sid]:
            course_group_rows.append((uid(), cid, gid))
        school_students = [s["id"] for s in all_students if s["school_id"] == sid]
        for cid in school_courses[sid]:
            for stu_id in school_students:
                enroll_rows.append((uid(), stu_id, cid))

    execute_values(
        cur,
        "INSERT INTO course_groups (id, course_id, group_id) VALUES %s",
        course_group_rows,
        template="(%s::uuid, %s::uuid, %s::uuid)",
    )
    execute_values(
        cur,
        "INSERT INTO enrollments (id, student_id, course_id) VALUES %s",
        enroll_rows,
        template="(%s::uuid, %s::uuid, %s::uuid)",
    )
    print(f"Created {len(course_group_rows)} course-group links, {len(enroll_rows)} enrollments.")

    # ── Assignments: 3 per course (monthly) ───────────────────────────────────
    assignment_rows = []
    course_assignments: dict[str, list[str]] = {}
    for sid in school_ids:
        for subj, cid in zip(SUBJECTS, school_courses[sid]):
            aids = []
            for month_i in range(3):
                aid = uid()
                due = base_date + timedelta(days=(month_i + 1) * 30)
                assignment_rows.append((aid, cid, f"{DEMO_PREFIX} {subj} ДЗ {month_i + 1}", f"Задание {month_i + 1} по {subj}", due, 100.0))
                aids.append(aid)
            course_assignments[cid] = aids

    execute_values(
        cur,
        "INSERT INTO assignments (id, course_id, title, description, due_date, max_score) VALUES %s",
        assignment_rows,
        template="(%s::uuid, %s::uuid, %s, %s, %s, %s)",
    )
    print(f"Created {len(assignment_rows)} assignments.")

    # ── Submissions + Grades ───────────────────────────────────────────────────
    submission_rows = []
    grade_rows = []

    for stu in all_students:
        sid = stu["school_id"]
        pattern = stu["pattern"]
        teacher_id = school_teacher[sid]

        for subj_idx, cid in enumerate(school_courses[sid]):
            scores = make_score_series(pattern, n=3)
            aids = course_assignments[cid]
            for month_i, (aid, score) in enumerate(zip(aids, scores)):
                sub_id = uid()
                submitted_at = base_date + timedelta(days=month_i * 30 + random.randint(0, 5))
                graded_at = submitted_at + timedelta(hours=random.randint(1, 48))
                level = score_to_level(score)

                submission_rows.append((
                    sub_id, aid, stu["id"],
                    f"submissions/{stu['id']}/{aid}.pdf",
                    f"hw_{month_i+1}.pdf",
                    random.randint(50000, 500000),
                    "graded",
                    submitted_at,
                ))
                grade_rows.append((
                    uid(), sub_id, round(score, 1), 100.0,
                    FEEDBACK_TEMPLATES[level],
                    teacher_id, True, graded_at,
                ))

    execute_values(
        cur,
        """
        INSERT INTO submissions
            (id, assignment_id, student_id, file_key, file_name, file_size, status, submitted_at)
        VALUES %s
        """,
        submission_rows,
        template="(%s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s, %s)",
    )
    execute_values(
        cur,
        """
        INSERT INTO grades
            (id, submission_id, score, max_score, feedback, graded_by_id, is_ai_graded, graded_at)
        VALUES %s
        """,
        grade_rows,
        template="(%s::uuid, %s::uuid, %s, %s, %s, %s::uuid, %s, %s)",
    )
    print(f"Created {len(submission_rows)} submissions and {len(grade_rows)} grades.")

    # ── Analytics: predictions per student per subject ─────────────────────────
    prediction_rows = []
    for stu in all_students:
        sid = stu["school_id"]
        for subj, cid in zip(SUBJECTS, school_courses[sid]):
            course_name = f"{DEMO_PREFIX} {subj}"
            prob = round(random.uniform(0.35, 0.97), 3)
            if stu["pattern"] == "strong":
                prob = round(random.uniform(0.70, 0.97), 3)
            elif stu["pattern"] == "weak":
                prob = round(random.uniform(0.35, 0.60), 3)
            prediction_rows.append((stu["id"], course_name, prob))

    execute_values(
        cur,
        "INSERT INTO anlt_predictions (student_id, subject, exam_pass_probability) VALUES %s",
        prediction_rows,
        template="(%s::uuid, %s, %s)",
    )
    print(f"Created {len(prediction_rows)} predictions.")

    # ── Analytics: regional recommendations ───────────────────────────────────
    rec_templates = [
        ["Направить методистов в слабые школы — прогноз +10 баллов за 30 дней.",
         "Организовать онлайн-марафон по слабым темам с охватом 200+ учеников.",
         "Ввести еженедельный мониторинг ДЗ и уведомления для родителей."],
        ["Провести тренинг учителей по интерактивным методам обучения.",
         "Обеспечить учебниками нового поколения 5+ школ.",
         "Запустить программу наставничества: сильные ученики помогают слабым."],
        ["Увеличить количество практических занятий на 2 часа в неделю.",
         "Стандартизировать критерии оценивания по всем школам региона.",
         "Проводить регулярный анализ типичных ошибок учеников."],
    ]
    rec_rows = []
    for i, region in enumerate(REGIONS):
        actions = rec_templates[i % len(rec_templates)]
        rec_rows.append((region, "regional", json.dumps({"actions": actions})))

    execute_values(
        cur,
        "INSERT INTO anlt_recommendations (region_name, level, content) VALUES %s",
        rec_rows,
        template="(%s, %s, %s::jsonb)",
    )
    print(f"Created {len(rec_rows)} regional recommendations.")

    conn.commit()
    cur.close()
    conn.close()

    print("\n=== Demo data summary ===")
    print(f"  Regions:         {len(REGIONS)}")
    print(f"  Schools:         {len(school_ids)}")
    print(f"  Students:        {len(all_students)}")
    print(f"  Courses:         {len(course_rows)}")
    print(f"  Assignments:     {len(assignment_rows)}")
    print(f"  Submissions:     {len(submission_rows)}")
    print(f"  Grades:          {len(grade_rows)}")
    print(f"  Predictions:     {len(prediction_rows)}")
    print(f"  Recommendations: {len(rec_rows)}")
    print("All done! Run: docker compose exec analytics python generate_demo_data_studyportal.py")


if __name__ == "__main__":
    main()
