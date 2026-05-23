from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def handle_homework_submit(payload: dict, db: AsyncSession) -> None:
    await db.execute(
        text("""
            INSERT INTO homework_submissions (id, student_id, assignment_id, file_key, submitted_at)
            VALUES (:id, :student_id, :assignment_id, :file_key, NOW())
            ON CONFLICT (id) DO NOTHING
        """),
        payload,
    )
    await db.commit()
