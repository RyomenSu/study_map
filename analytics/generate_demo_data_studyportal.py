"""
Generate synthetic demo data for the current Study-Map schema (studyportal DB).

Creates:
- demo schools/teacher/students/groups
- demo courses/assignments/enrollments
- demo submissions + grades (historical spread)
- demo analytics rows in anlt_predictions/anlt_recommendations

Run inside analytics container:
    python generate_demo_data_studyportal.py
"""

from __future__ import annotations

import json
import os
import random
import uuid
from datetime import datetime, timedelta

import psycopg2

DEMO_PREFIX = "Demo"
DEMO_TEACHER_EMAIL = "demo.teacher@studymap.local"
# bcrypt hash for password: "password"
DEMO_PASSWORD_HASH = "$2b$12$KIXQ4Jf4Qw5A3FihZlym9eJ5N8P2QBX4fQf2x3D6xJ4VvB9iY6YfK"


def _pg_url() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql://studyportal:studyportal_pass@localhost:5432/studyportal",
    ).strip()
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://") :]
    return url


def _cleanup_demo(cur) -> None:
    # Collect demo ids first.
    cur.execute(
        "SELECT id FROM users WHERE email LIKE 'demo.student.%%@studymap.local' OR email = %s",
        (DEMO_TEACHER_EMAIL,),
    )
    demo_user_ids = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT id FROM schools WHERE name LIKE %s", (f"{DEMO_PREFIX} School %",))
    demo_school_ids = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT id FROM groups WHERE name LIKE %s", (f"{DEMO_PREFIX} Group %",))
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

    if demo_user_ids:
        cur.execute("DELETE FROM attendance_records WHERE student_id = ANY(%s::uuid[])", (demo_user_ids,))
        cur.execute("DELETE FROM users WHERE id = ANY(%s::uuid[])", (demo_user_ids,))

    if demo_group_ids:
        cur.execute("DELETE FROM groups WHERE id = ANY(%s::uuid[])", (demo_group_ids,))

    if demo_school_ids:
        cur.execute("DELETE FROM schools WHERE id = ANY(%s::uuid[])", (demo_school_ids,))

    cur.execute("DELETE FROM anlt_predictions WHERE subject LIKE %s", (f"{DEMO_PREFIX}-%",))
    cur.execute("DELETE FROM anlt_recommendations WHERE region_name LIKE %s", (f"{DEMO_PREFIX} Region %",))


def main() -> None:
    random.seed(42)
    conn = psycopg2.connect(_pg_url())
    conn.autocommit = False
    cur = conn.cursor()

    _cleanup_demo(cur)

    # Schools
    schools = []
    for i, region in enumerate(["Demo Region A", "Demo Region B"], start=1):
        school_id = str(uuid.uuid4())
        schools.append((school_id, f"{DEMO_PREFIX} School {i}", region, f"City {i}"))
    cur.executemany(
        "INSERT INTO schools (id, name, region, city) VALUES (%s::uuid, %s, %s, %s)",
        schools,
    )

    school_ids = [row[0] for row in schools]

    # Groups
    groups = []
    for i, school_id in enumerate(school_ids, start=1):
        groups.append((str(uuid.uuid4()), f"{DEMO_PREFIX} Group {i}", school_id))
    cur.executemany(
        "INSERT INTO groups (id, name, school_id) VALUES (%s::uuid, %s, %s::uuid)",
        groups,
    )
    group_ids = [row[0] for row in groups]

    # Teacher
    teacher_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO users (id, email, password_hash, full_name, role, school_id, is_active)
        VALUES (%s::uuid, %s, %s, %s, 'teacher', %s::uuid, TRUE)
        """,
        (teacher_id, DEMO_TEACHER_EMAIL, DEMO_PASSWORD_HASH, "Demo Teacher", school_ids[0]),
    )

    # Students
    students = []
    for i in range(1, 21):
        school_id = school_ids[0] if i <= 10 else school_ids[1]
        group_id = group_ids[0] if i <= 10 else group_ids[1]
        students.append(
            (
                str(uuid.uuid4()),
                f"demo.student.{i}@studymap.local",
                DEMO_PASSWORD_HASH,
                f"Demo Student {i}",
                school_id,
                group_id,
            )
        )
    cur.executemany(
        """
        INSERT INTO users (id, email, password_hash, full_name, role, school_id, group_id, is_active)
        VALUES (%s::uuid, %s, %s, %s, 'student', %s::uuid, %s::uuid, TRUE)
        """,
        students,
    )

    student_ids = [row[0] for row in students]

    # Courses + assignments
    courses = [
        (str(uuid.uuid4()), f"{DEMO_PREFIX} History", "Demo history course", teacher_id, school_ids[0]),
        (str(uuid.uuid4()), f"{DEMO_PREFIX} Math", "Demo math course", teacher_id, school_ids[1]),
    ]
    cur.executemany(
        """
        INSERT INTO courses (id, name, description, teacher_id, school_id)
        VALUES (%s::uuid, %s, %s, %s::uuid, %s::uuid)
        """,
        courses,
    )
    course_ids = [row[0] for row in courses]

    # Link groups to courses
    course_groups = [
        (str(uuid.uuid4()), course_ids[0], group_ids[0]),
        (str(uuid.uuid4()), course_ids[1], group_ids[1]),
    ]
    cur.executemany(
        "INSERT INTO course_groups (id, course_id, group_id) VALUES (%s::uuid, %s::uuid, %s::uuid)",
        course_groups,
    )

    # Enroll students
    enroll_rows = []
    for sid in student_ids[:10]:
        enroll_rows.append((str(uuid.uuid4()), sid, course_ids[0]))
    for sid in student_ids[10:]:
        enroll_rows.append((str(uuid.uuid4()), sid, course_ids[1]))
    cur.executemany(
        "INSERT INTO enrollments (id, student_id, course_id) VALUES (%s::uuid, %s::uuid, %s::uuid)",
        enroll_rows,
    )

    now = datetime.utcnow()
    assignments = [
        (str(uuid.uuid4()), course_ids[0], f"{DEMO_PREFIX} History HW 1", "Causes of WWII", now - timedelta(days=20), 100.0),
        (str(uuid.uuid4()), course_ids[0], f"{DEMO_PREFIX} History HW 2", "Cold War basics", now - timedelta(days=10), 100.0),
        (str(uuid.uuid4()), course_ids[1], f"{DEMO_PREFIX} Math HW 1", "Algebra basics", now - timedelta(days=20), 100.0),
        (str(uuid.uuid4()), course_ids[1], f"{DEMO_PREFIX} Math HW 2", "Geometry basics", now - timedelta(days=10), 100.0),
    ]
    cur.executemany(
        """
        INSERT INTO assignments (id, course_id, title, description, due_date, max_score)
        VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s)
        """,
        assignments,
    )

    assignment_ids = [row[0] for row in assignments]

    # Submissions + grades
    submissions = []
    grades = []
    score_bands = [42, 55, 63, 71, 78, 84, 91]
    for idx, sid in enumerate(student_ids):
        is_history = idx < 10
        sub_assignment_ids = assignment_ids[:2] if is_history else assignment_ids[2:]
        for j, aid in enumerate(sub_assignment_ids):
            sub_id = str(uuid.uuid4())
            score = float(score_bands[(idx + j) % len(score_bands)])
            submitted_at = now - timedelta(days=18 - (j * 6) + (idx % 3))
            submissions.append(
                (
                    sub_id,
                    aid,
                    sid,
                    f"submissions/{sid}/{aid}.pdf",
                    f"{DEMO_PREFIX.lower()}_{idx+1}_{j+1}.pdf",
                    123456,
                    "graded",
                    submitted_at,
                )
            )
            grades.append(
                (
                    str(uuid.uuid4()),
                    sub_id,
                    score,
                    100.0,
                    f"{DEMO_PREFIX} feedback: solid work with room to improve.",
                    teacher_id,
                    True,
                    submitted_at + timedelta(hours=2),
                )
            )

    cur.executemany(
        """
        INSERT INTO submissions
            (id, assignment_id, student_id, file_key, file_name, file_size, status, submitted_at)
        VALUES (%s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s, %s)
        """,
        submissions,
    )

    cur.executemany(
        """
        INSERT INTO grades
            (id, submission_id, score, max_score, feedback, graded_by_id, is_ai_graded, graded_at)
        VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s::uuid, %s, %s)
        """,
        grades,
    )

    # Seed analytics projections/recommendations for immediate dashboard visibility.
    predictions = []
    for sid in student_ids:
        for subject in [f"{DEMO_PREFIX}-History", f"{DEMO_PREFIX}-Math"]:
            prob = round(random.uniform(0.45, 0.97), 3)
            predictions.append((sid, subject, prob))
    cur.executemany(
        """
        INSERT INTO anlt_predictions (student_id, subject, exam_pass_probability)
        VALUES (%s::uuid, %s, %s)
        """,
        predictions,
    )

    recommendations = [
        (
            f"{DEMO_PREFIX} Region A",
            "regional",
            json.dumps(
                {
                    "actions": [
                        "Launch weekly remedial history sessions for low performers.",
                        "Assign peer mentors from top quartile students.",
                        "Track homework completion daily and notify parents automatically.",
                    ]
                }
            ),
        ),
        (
            f"{DEMO_PREFIX} Region B",
            "regional",
            json.dumps(
                {
                    "actions": [
                        "Increase math problem-solving labs by 2 hours per week.",
                        "Standardize grading rubrics across schools.",
                        "Run targeted teacher workshops on common error patterns.",
                    ]
                }
            ),
        ),
    ]
    cur.executemany(
        """
        INSERT INTO anlt_recommendations (region_name, level, content)
        VALUES (%s, %s, %s::jsonb)
        """,
        recommendations,
    )

    conn.commit()
    cur.close()
    conn.close()
    print("Demo data created for studyportal schema.")
    print("Created: 2 schools, 2 groups, 1 teacher, 20 students, 2 courses, 4 assignments, 40 submissions/grades.")


if __name__ == "__main__":
    main()
