from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def handle_attendance_mark(payload: dict, db: AsyncSession) -> None:
    await db.execute(
        text("""
            INSERT INTO attendance (id, student_id, course_id, date, status, created_at)
            VALUES (:id, :student_id, :course_id, :date, :status, NOW())
            ON CONFLICT (id) DO NOTHING
        """),
        payload,
    )
    await db.commit()
