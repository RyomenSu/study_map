import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUser, TeacherOrAdmin
from app.models import Grade, Submission, SubmissionStatus, User, UserRole
from app.schemas import GradeCreate, GradeOut

router = APIRouter(tags=["grades"])


@router.post("/submissions/{submission_id}/grade", response_model=GradeOut, status_code=201, dependencies=[TeacherOrAdmin])
async def grade_submission(
    submission_id: uuid.UUID,
    body: GradeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    existing = await db.execute(select(Grade).where(Grade.submission_id == submission_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already graded. Use PUT to update.")

    from app.models import Assignment
    asgn_result = await db.execute(select(Assignment).where(Assignment.id == sub.assignment_id))
    asgn = asgn_result.scalar_one_or_none()

    grade = Grade(
        submission_id=submission_id,
        score=body.score,
        max_score=asgn.max_score if asgn else 100.0,
        feedback=body.feedback,
        graded_by_id=current_user.id,
    )

    sub.status = SubmissionStatus.graded
    db.add(grade)
    await db.commit()
    await db.refresh(grade)
    return grade


@router.put("/submissions/{submission_id}/grade", response_model=GradeOut, dependencies=[TeacherOrAdmin])
async def update_grade(
    submission_id: uuid.UUID,
    body: GradeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(select(Grade).where(Grade.submission_id == submission_id))
    grade = result.scalar_one_or_none()
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")

    grade.score = body.score
    grade.feedback = body.feedback
    grade.graded_by_id = current_user.id
    await db.commit()
    await db.refresh(grade)
    return grade


@router.get("/courses/{course_id}/grades", response_model=list[dict])
async def course_grades(
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    from app.models import Assignment
    asgn_result = await db.execute(select(Assignment).where(Assignment.course_id == course_id))
    assignments = asgn_result.scalars().all()
    asgn_ids = [a.id for a in assignments]

    query = select(Submission).where(Submission.assignment_id.in_(asgn_ids))
    if current_user.role == UserRole.student:
        query = query.where(Submission.student_id == current_user.id)

    sub_result = await db.execute(query)
    submissions = sub_result.scalars().all()

    rows = []
    for sub in submissions:
        grade_result = await db.execute(select(Grade).where(Grade.submission_id == sub.id))
        grade = grade_result.scalar_one_or_none()
        student_result = await db.execute(select(User).where(User.id == sub.student_id))
        student = student_result.scalar_one_or_none()
        rows.append({
            "submission_id": str(sub.id),
            "assignment_id": str(sub.assignment_id),
            "student_id": str(sub.student_id),
            "student_name": student.full_name if student else None,
            "status": sub.status.value,
            "score": grade.score if grade else None,
            "max_score": grade.max_score if grade else None,
            "feedback": grade.feedback if grade else None,
        })
    return rows
