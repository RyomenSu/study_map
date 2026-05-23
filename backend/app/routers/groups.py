import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUser, TeacherOrAdmin
from app.models import CourseGroup, Enrollment, Group, User, UserRole
from app.schemas import AssignGroupRequest, AssignStudentToGroupRequest, GroupCreate, GroupOut, UserOut

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("", response_model=GroupOut, status_code=201, dependencies=[TeacherOrAdmin])
async def create_group(body: GroupCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    group = Group(**body.model_dump())
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


@router.get("", response_model=list[GroupOut])
async def list_groups(db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser):
    result = await db.execute(select(Group))
    return result.scalars().all()


@router.get("/{group_id}", response_model=GroupOut)
async def get_group(group_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser):
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.get("/{group_id}/members", response_model=list[UserOut])
async def group_members(group_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser):
    result = await db.execute(select(User).where(User.group_id == group_id))
    return result.scalars().all()


@router.post("/{group_id}/members", response_model=UserOut, dependencies=[TeacherOrAdmin])
async def add_student_to_group(
    group_id: uuid.UUID,
    body: AssignStudentToGroupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.id == body.student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.role != UserRole.student:
        raise HTTPException(status_code=400, detail="User is not a student")

    student.group_id = group_id
    await db.commit()
    await db.refresh(student)
    return student


@router.delete("/{group_id}/members/{student_id}", status_code=204, dependencies=[TeacherOrAdmin])
async def remove_student_from_group(
    group_id: uuid.UUID,
    student_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.id == student_id, User.group_id == group_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not in this group")
    student.group_id = None
    await db.commit()


@router.post("/courses/{course_id}/assign-group", dependencies=[TeacherOrAdmin])
async def assign_group_to_course(
    course_id: uuid.UUID,
    body: AssignGroupRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Assign a group to a course and auto-enroll all current group members."""
    # prevent duplicate CourseGroup
    existing_cg = await db.execute(
        select(CourseGroup).where(
            CourseGroup.course_id == course_id,
            CourseGroup.group_id == body.group_id,
        )
    )
    if existing_cg.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Group already assigned to this course")

    course_group = CourseGroup(course_id=course_id, group_id=body.group_id)
    db.add(course_group)

    # bulk enroll all students in the group who aren't already enrolled
    students_result = await db.execute(
        select(User).where(User.group_id == body.group_id, User.role == UserRole.student)
    )
    students = students_result.scalars().all()

    enrolled_count = 0
    for student in students:
        already = await db.execute(
            select(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.student_id == student.id,
            )
        )
        if not already.scalar_one_or_none():
            db.add(Enrollment(course_id=course_id, student_id=student.id))
            enrolled_count += 1

    await db.commit()
    return {"enrolled": enrolled_count, "group_id": str(body.group_id), "course_id": str(course_id)}


@router.get("/courses/{course_id}/groups")
async def course_groups(
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(
        select(Group)
        .join(CourseGroup, CourseGroup.group_id == Group.id)
        .where(CourseGroup.course_id == course_id)
    )
    groups = result.scalars().all()
    return [{"id": str(g.id), "name": g.name} for g in groups]
