"""
Temporary development-only endpoints. Remove before going to production.
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthUser, require_role
from app.config import settings
from app.db.session import get_db
from app.events import schemas, topics
from app.kafka import producer
from app.storage.s3 import upload_file

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/homework/upload", status_code=201, dependencies=[Depends(require_role("student", "teacher", "admin"))])
async def upload_homework(
    student_id: str = Form(...),
    assignment_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if settings.env == "production":
        raise HTTPException(status_code=404)

    key = f"homework/{assignment_id}/{student_id}/{uuid.uuid4()}_{file.filename}"
    await upload_file(file, key)

    submission_id = str(uuid.uuid4())
    await db.execute(
        text("""
            INSERT INTO homework_submissions (id, student_id, assignment_id, file_key, status, submitted_at)
            VALUES (:id, :student_id, :assignment_id, :file_key, 'pending', NOW())
        """),
        {"id": submission_id, "student_id": student_id, "assignment_id": assignment_id, "file_key": key},
    )
    await db.commit()

    event = schemas.HomeworkSubmitEvent(
        payload={
            "id": submission_id,
            "student_id": student_id,
            "assignment_id": assignment_id,
            "file_key": key,
        }
    )
    await producer.publish(topics.HOMEWORK_SUBMITTED, event.model_dump(mode="json"))

    return {
        "id": submission_id,
        "file_key": key,
        "event_id": event.event_id,
    }
