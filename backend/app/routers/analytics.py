"""Regional analytics — compares school performance metrics across regions."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUser
from app.models import (
    AttendanceRecord, AttendanceSession, Course, Enrollment, Grade,
    School, Submission, User, UserRole,
)
from app.schemas import SchoolMetrics

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/schools", response_model=list[SchoolMetrics])
async def school_metrics(db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser):
    schools_result = await db.execute(select(School))
    schools = schools_result.scalars().all()

    metrics = []
    for school in schools:
        # student count
        student_count_result = await db.execute(
            select(func.count(User.id)).where(User.school_id == school.id, User.role == UserRole.student)
        )
        total_students = student_count_result.scalar_one() or 0

        # course count
        course_count_result = await db.execute(
            select(func.count(Course.id)).where(Course.school_id == school.id)
        )
        total_courses = course_count_result.scalar_one() or 0

        # avg grade
        avg_grade_result = await db.execute(
            select(func.avg(Grade.score / Grade.max_score * 100))
            .join(Submission, Submission.id == Grade.submission_id)
            .join(User, User.id == Submission.student_id)
            .where(User.school_id == school.id)
        )
        avg_grade = avg_grade_result.scalar_one()

        # attendance rate
        total_records_result = await db.execute(
            select(func.count(AttendanceRecord.id))
            .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
            .join(Course, Course.id == AttendanceSession.course_id)
            .join(User, User.id == AttendanceRecord.student_id)
            .where(Course.school_id == school.id)
        )
        total_records = total_records_result.scalar_one() or 0

        present_result = await db.execute(
            select(func.count(AttendanceRecord.id))
            .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
            .join(Course, Course.id == AttendanceSession.course_id)
            .join(User, User.id == AttendanceRecord.student_id)
            .where(Course.school_id == school.id, AttendanceRecord.status.in_(["present", "late"]))
        )
        present_count = present_result.scalar_one() or 0
        attendance_rate = round(present_count / total_records * 100, 1) if total_records else None

        metrics.append(SchoolMetrics(
            school_id=school.id,
            school_name=school.name,
            region=school.region,
            city=school.city,
            avg_grade=round(avg_grade, 1) if avg_grade is not None else None,
            attendance_rate=attendance_rate,
            total_students=total_students,
            total_courses=total_courses,
        ))

    return metrics


@router.get("/regions")
async def region_metrics(db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser):
    """Aggregate metrics grouped by region for map coloring."""
    result = await db.execute(
        select(
            School.region,
            func.avg(Grade.score / Grade.max_score * 100).label("avg_grade"),
            func.count(User.id.distinct()).label("total_students"),
        )
        .join(Course, Course.school_id == School.id)
        .join(User, User.school_id == School.id)
        .outerjoin(Enrollment, Enrollment.student_id == User.id)
        .outerjoin(Submission, Submission.student_id == User.id)
        .outerjoin(Grade, Grade.submission_id == Submission.id)
        .group_by(School.region)
    )
    rows = result.all()
    return [
        {
            "region": r.region,
            "avg_grade": round(r.avg_grade, 1) if r.avg_grade else None,
            "total_students": r.total_students,
        }
        for r in rows
    ]
