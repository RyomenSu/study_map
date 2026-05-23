import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import CurrentUser, TeacherOrAdmin
from app.models import Course, Enrollment, User, UserRole
from app.schemas import CourseCreate, CourseOut, EnrollRequest, EnrollmentOut

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("", response_model=CourseOut, status_code=201, dependencies=[TeacherOrAdmin])
async def create_course(
    body: CourseCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    course = Course(**body.model_dump(), teacher_id=current_user.id)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.get("", response_model=list[CourseOut])
async def list_courses(db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser):
    if current_user.role == UserRole.student:
        result = await db.execute(
            select(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.student_id == current_user.id)
        )
    elif current_user.role == UserRole.teacher:
        result = await db.execute(select(Course).where(Course.teacher_id == current_user.id))
    else:
        result = await db.execute(select(Course))
    return result.scalars().all()


@router.get("/{course_id}", response_model=CourseOut)
async def get_course(course_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.post("/{course_id}/enroll", response_model=EnrollmentOut, dependencies=[TeacherOrAdmin])
async def enroll_student(
    course_id: uuid.UUID,
    body: EnrollRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    existing = await db.execute(
        select(Enrollment).where(
            Enrollment.course_id == course_id,
            Enrollment.student_id == body.student_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already enrolled")

    enrollment = Enrollment(course_id=course_id, student_id=body.student_id)
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@router.get("/{course_id}/students", response_model=list[dict])
async def course_students(
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(
        select(User)
        .join(Enrollment, Enrollment.student_id == User.id)
        .where(Enrollment.course_id == course_id)
    )
    students = result.scalars().all()
    return [{"id": str(s.id), "full_name": s.full_name, "email": s.email} for s in students]
