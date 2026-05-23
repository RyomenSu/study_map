"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enums
    user_role = sa.Enum("student", "teacher", "admin", name="user_role")
    submission_status = sa.Enum("pending", "graded", name="submission_status")
    attendance_status = sa.Enum("present", "absent", "late", "excused", name="attendance_status")

    user_role.create(op.get_bind(), checkfirst=True)
    submission_status.create(op.get_bind(), checkfirst=True)
    attendance_status.create(op.get_bind(), checkfirst=True)

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("student", "teacher", "admin", name="user_role"), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    # courses
    op.create_table(
        "courses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("teacher_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_courses_teacher_id", "courses", ["teacher_id"])

    # enrollments
    op.create_table(
        "enrollments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_enrollments_student_course", "enrollments", ["student_id", "course_id"])
    op.create_index("ix_enrollments_course_id", "enrollments", ["course_id"])

    # assignments
    op.create_table(
        "assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_assignments_course_id", "assignments", ["course_id"])
    op.create_index("ix_assignments_due_date", "assignments", ["due_date"])

    # homework_submissions
    op.create_table(
        "homework_submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_id", sa.String(36), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_key", sa.String(512), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "graded", name="submission_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("grade", sa.Numeric(5, 2), nullable=True),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_submissions_student_assignment", "homework_submissions", ["student_id", "assignment_id"]
    )
    op.create_index("ix_submissions_assignment_id", "homework_submissions", ["assignment_id"])
    op.create_index("ix_submissions_status", "homework_submissions", ["status"])

    # attendance
    op.create_table(
        "attendance",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column(
            "status",
            sa.Enum("present", "absent", "late", "excused", name="attendance_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint(
        "uq_attendance_student_course_date", "attendance", ["student_id", "course_id", "date"]
    )
    op.create_index("ix_attendance_course_date", "attendance", ["course_id", "date"])
    op.create_index("ix_attendance_student_id", "attendance", ["student_id"])


def downgrade() -> None:
    op.drop_table("attendance")
    op.drop_table("homework_submissions")
    op.drop_table("assignments")
    op.drop_table("enrollments")
    op.drop_table("courses")
    op.drop_table("users")

    sa.Enum(name="attendance_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="submission_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
