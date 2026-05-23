"""
Temporary development-only endpoints. Remove before going to production.
"""
import uuid
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import settings
from app.events import schemas, topics
from app.kafka import producer
from app.storage.s3 import upload_file

router = APIRouter(prefix="/dev", tags=["dev"])

SEED_ADMIN = {
    "id": "00000000-0000-0000-0000-000000000001",
    "name": "Admin",
    "email": "admin@studymap.local",
    "role": "admin",
    "password_hash": None,
}


@router.post("/seed/admin", status_code=202)
async def seed_admin() -> dict[str, Any]:
    if settings.env == "production":
        raise HTTPException(status_code=404)

    event = schemas.UserCreateEvent(payload=SEED_ADMIN)
    await producer.publish(topics.USERS, event.model_dump(mode="json"))
    return {
        "accepted": True,
        "event_id": event.event_id,
        "note": "Admin user event published — worker will insert into DB.",
        "credentials": {"email": SEED_ADMIN["email"]},
    }


@router.post("/homework/upload", status_code=202)
async def upload_homework(
    student_id: str = Form(...),
    assignment_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    if settings.env == "production":
        raise HTTPException(status_code=404)

    key = f"homework/{assignment_id}/{student_id}/{uuid.uuid4()}_{file.filename}"
    await upload_file(file, key)

    event = schemas.HomeworkSubmitEvent(
        payload={
            "id": str(uuid.uuid4()),
            "student_id": student_id,
            "assignment_id": assignment_id,
            "file_key": key,
        }
    )
    await producer.publish(topics.HOMEWORK, event.model_dump(mode="json"))
    return {
        "accepted": True,
        "event_id": event.event_id,
        "file_key": key,
        "note": "File uploaded to S3. Submission event published — worker will insert into DB.",
    }
