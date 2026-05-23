import uuid
from datetime import datetime
from typing import Literal, Any
from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    event_id: str
    occurred_at: datetime
    action: str
    payload: dict[str, Any]
