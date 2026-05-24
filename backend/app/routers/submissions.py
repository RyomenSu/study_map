import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUser, TeacherOrAdmin
from app.models import Assignment, Grade, Submission, SubmissionStatus, UserRole
from app.schemas import SubmissionOut, SubmissionWithDownload
from app.services import storage
from app.services.kafka import publish_submission

router = APIRouter(tags=["submissions"])


@router.post("/courses/{course_id}/assignments/{assignment_id}/submit", response_model=SubmissionOut, status_code=201)
async def submit_homework(
    course_id: uuid.UUID,
    assignment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    file: Optional[UploadFile] = File(None),
    notes: Optional[str] = Form(None),
):
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id, Assignment.course_id == course_id))
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    file_key = None
    file_name = None
    file_size = None

    if file:
        contents = await file.read()
        file_key = storage.upload_file(contents, file.filename, file.content_type or "application/octet-stream")
        file_name = file.filename
        file_size = len(contents)

    # check if late
    from datetime import datetime, timezone
    status_val = SubmissionStatus.submitted
    if assignment.due_date and datetime.now(timezone.utc) > assignment.due_date.replace(tzinfo=timezone.utc):
        status_val = SubmissionStatus.late

    submission = Submission(
        assignment_id=assignment_id,
        student_id=current_user.id,
        file_key=file_key,
        file_name=file_name,
        file_size=file_size,
        notes=notes,
        status=status_val,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    if file_key:
        try:
            await publish_submission(
                submission_id=str(submission.id),
                student_id=str(current_user.id),
                assignment_id=str(assignment_id),
                file_path=file_key,
            )
        except Exception as e:
            # Grading is async — don't fail the submission if Kafka is down
            print(f"Warning: could not publish to Kafka: {e}")

    return submission


@router.get("/courses/{course_id}/assignments/{assignment_id}/submissions", response_model=list[SubmissionWithDownload])
async def list_submissions(
    course_id: uuid.UUID,
    assignment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    query = select(Submission).where(Submission.assignment_id == assignment_id)
    if current_user.role == UserRole.student:
        query = query.where(Submission.student_id == current_user.id)

    result = await db.execute(query)
    subs = result.scalars().all()

    out = []
    for s in subs:
        data = SubmissionWithDownload.model_validate(s)
        grade_result = await db.execute(select(Grade).where(Grade.submission_id == s.id))
        grade = grade_result.scalar_one_or_none()
        if grade:
            data.score = grade.score
            data.max_score = grade.max_score
            data.feedback = grade.feedback
        if s.file_key:
            data.download_url = storage.generate_presigned_url(s.file_key)
        out.append(data)
    return out


@router.get("/submissions/{submission_id}/download")
async def download_submission(
    submission_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if current_user.role == UserRole.student and sub.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not sub.file_key:
        raise HTTPException(status_code=404, detail="No file attached")

    url = storage.generate_presigned_url(sub.file_key)
    return {"download_url": url}
