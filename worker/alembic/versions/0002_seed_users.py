"""seed admin and test student users

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-23

"""
from typing import Sequence, Union

from alembic import op
from passlib.hash import bcrypt

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADMIN_ID = "00000000-0000-0000-0000-000000000001"
STUDENT_ID = "00000000-0000-0000-0000-000000000002"


def upgrade() -> None:
    admin_hash = bcrypt.hash("admin123")
    student_hash = bcrypt.hash("student123")

    op.execute(f"""
        INSERT INTO users (id, name, email, role, password_hash, created_at, updated_at)
        VALUES
            ('{ADMIN_ID}',   'Admin',        'admin@studymap.local',   'admin',   '{admin_hash}',   NOW(), NOW()),
            ('{STUDENT_ID}', 'Test Student', 'student@studymap.local', 'student', '{student_hash}', NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute(f"""
        DELETE FROM users WHERE id IN ('{ADMIN_ID}', '{STUDENT_ID}')
    """)
