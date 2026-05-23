import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUser, TeacherOrAdmin
from app.models import Assignment, Course, Enrollment, UserRole
from app.schemas import AssignmentCreate, AssignmentOut

router = APIRouter(prefix="/courses/{course_id}/assignments", tags=["assignments"])


async def _get_course_or_404(course_id: uuid.UUID, db: AsyncSession) -> Course:
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.post("", response_model=AssignmentOut, status_code=201, dependencies=[TeacherOrAdmin])
async def create_assignment(
    course_id: uuid.UUID,
    body: AssignmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    await _get_course_or_404(course_id, db)
    assignment = Assignment(**body.model_dump(), course_id=course_id)
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.get("", response_model=list[AssignmentOut])
async def list_assignments(
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    await _get_course_or_404(course_id, db)
    result = await db.execute(select(Assignment).where(Assignment.course_id == course_id))
    return result.scalars().all()


@router.get("/{assignment_id}", response_model=AssignmentOut)
async def get_assignment(
    course_id: uuid.UUID,
    assignment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(
        select(Assignment).where(Assignment.id == assignment_id, Assignment.course_id == course_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.delete("/{assignment_id}", status_code=204, dependencies=[TeacherOrAdmin])
async def delete_assignment(
    course_id: uuid.UUID,
    assignment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Assignment).where(Assignment.id == assignment_id, Assignment.course_id == course_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await db.delete(assignment)
    await db.commit()
