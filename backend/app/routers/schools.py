from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import AdminOnly, CurrentUser
from app.models import School
from app.schemas import SchoolCreate, SchoolOut

router = APIRouter(prefix="/schools", tags=["schools"])


@router.post("", response_model=SchoolOut, status_code=201, dependencies=[AdminOnly])
async def create_school(body: SchoolCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    school = School(**body.model_dump())
    db.add(school)
    await db.commit()
    await db.refresh(school)
    return school


@router.get("", response_model=list[SchoolOut])
async def list_schools(db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser):
    result = await db.execute(select(School))
    return result.scalars().all()
