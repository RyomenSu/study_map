import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.events import schemas, topics
from app.kafka import producer

router = APIRouter(prefix="/users", tags=["users"])


class UserCreateRequest(BaseModel):
    name: str
    email: EmailStr
    role: str  # student | teacher | admin


@router.post("/", status_code=202)
async def create_user(body: UserCreateRequest) -> dict[str, Any]:
    event = schemas.UserCreateEvent(
        payload={
            "id": str(uuid.uuid4()),
            "name": body.name,
            "email": body.email,
            "role": body.role,
        }
    )
    await producer.publish(topics.USERS, event.model_dump(mode="json"))
    return {"accepted": True, "event_id": event.event_id}


@router.get("/{user_id}")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    row = await db.execute(
        text("SELECT id, name, email, role, created_at FROM users WHERE id = :id"),
        {"id": user_id},
    )
    user = row.mappings().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(user)


@router.get("/")
async def list_users(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    rows = await db.execute(
        text("SELECT id, name, email, role, created_at FROM users ORDER BY created_at DESC")
    )
    return [dict(r) for r in rows.mappings()]
