import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import CurrentUser, TeacherOrAdmin
from app.models import AttendanceRecord, AttendanceSession, Enrollment, UserRole
from app.schemas import AttendanceSessionCreate, AttendanceSessionOut

router = APIRouter(prefix="/courses/{course_id}/attendance", tags=["attendance"])


@router.post("", response_model=AttendanceSessionOut, status_code=201, dependencies=[TeacherOrAdmin])
async def create_session(
    course_id: uuid.UUID,
    body: AttendanceSessionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    session = AttendanceSession(
        course_id=course_id,
        session_date=body.session_date,
        created_by_id=current_user.id,
    )
    db.add(session)
    await db.flush()

    for rec in body.records:
        db.add(AttendanceRecord(
            session_id=session.id,
            student_id=rec.student_id,
            status=rec.status,
            notes=rec.notes,
        ))

    await db.commit()

    result = await db.execute(
        select(AttendanceSession)
        .options(selectinload(AttendanceSession.records))
        .where(AttendanceSession.id == session.id)
    )
    return result.scalar_one()


@router.get("", response_model=list[AttendanceSessionOut])
async def list_sessions(
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(
        select(AttendanceSession)
        .options(selectinload(AttendanceSession.records))
        .where(AttendanceSession.course_id == course_id)
        .order_by(AttendanceSession.session_date.desc())
    )
    sessions = result.scalars().all()

    # Students only see their own records
    if current_user.role == UserRole.student:
        for s in sessions:
            s.records = [r for r in s.records if r.student_id == current_user.id]

    return sessions


@router.get("/summary")
async def attendance_summary(
    course_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    total_sessions_result = await db.execute(
        select(func.count()).where(AttendanceSession.course_id == course_id)
    )
    total_sessions = total_sessions_result.scalar_one()

    query = (
        select(
            AttendanceRecord.student_id,
            AttendanceRecord.status,
            func.count().label("count"),
        )
        .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
        .where(AttendanceSession.course_id == course_id)
        .group_by(AttendanceRecord.student_id, AttendanceRecord.status)
    )

    if current_user.role == UserRole.student:
        query = query.where(AttendanceRecord.student_id == current_user.id)

    result = await db.execute(query)
    rows = result.all()

    summary: dict[str, dict] = {}
    for student_id, status, count in rows:
        sid = str(student_id)
        if sid not in summary:
            summary[sid] = {"student_id": sid, "present": 0, "absent": 0, "late": 0, "excused": 0, "total_sessions": total_sessions}
        summary[sid][status.value] += count

    for s in summary.values():
        attended = s["present"] + s["late"]
        s["attendance_rate"] = round(attended / total_sessions * 100, 1) if total_sessions else 0

    return list(summary.values())
