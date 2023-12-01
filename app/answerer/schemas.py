from pydantic import BaseModel

from app.db.enums import AnswerType


class WebhookPayload(BaseModel):
    entry: list
    object: str


class AnswerOutput(BaseModel):
    answer: str | None
    type: AnswerType
    user_id: int | None = None
    used_event_ids: list[int] | None = None
