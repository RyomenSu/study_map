from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUser, TeacherOrAdmin
from app.models import User, UserRole
from app.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut], dependencies=[TeacherOrAdmin])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    role: str | None = None,
):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    result = await db.execute(query.order_by(User.full_name))
    return result.scalars().all()
