from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def handle_user_create(payload: dict, db: AsyncSession) -> None:
    await db.execute(
        text("""
            INSERT INTO users (id, name, email, role, created_at)
            VALUES (:id, :name, :email, :role, NOW())
            ON CONFLICT (id) DO NOTHING
        """),
        payload,
    )
    await db.commit()
