from enum import Enum

from pydantic import BaseModel

from app.db.enums import AnswerType


class WebhookPayload(BaseModel):
    entry: list
    object: str


class MessageInput(BaseModel):
    wa_id: str
    phone_number: str
    body: str
    timestamp: int


class AnswerOutput(BaseModel):
    answer: str | None
    type: AnswerType
    user_id: int | None = None
    used_event_ids: list[int] | None = None


class DayTimeEnum(str, Enum):
    daytime = "daytime"
    nighttime = "nighttime"
    entire_day = "entire_day"
