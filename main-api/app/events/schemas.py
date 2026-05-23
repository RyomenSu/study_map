import uuid
from datetime import datetime
from typing import Literal, Any
from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreateEvent(BaseEvent):
    action: Literal["user.create"] = "user.create"
    payload: dict[str, Any]


class AttendanceMarkEvent(BaseEvent):
    action: Literal["attendance.mark"] = "attendance.mark"
    payload: dict[str, Any]


class HomeworkSubmitEvent(BaseEvent):
    action: Literal["homework.submit"] = "homework.submit"
    payload: dict[str, Any]
