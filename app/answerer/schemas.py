from typing import Optional

from pydantic import BaseModel, Field

from app.db.enums import AnswerType


class WebhookPayload(BaseModel):
    entry: list
    object: str


class AnswerOutput(BaseModel):
    answer: str | None
    type: AnswerType
    used_event_ids: list[int] | None = None


class SearchEventsToolInput(BaseModel):
    user_query: str = Field(description="The user's query")
    start_date: Optional[str] = Field(
        description="The start date of the range in format 'YYYY-MM-DD'"
    )
    end_date: Optional[str] = Field(
        description="The end date of the range in format 'YYYY-MM-DD'"
    )
    time: Optional[str] = Field(
        description="This is the time of the day. It can be either 'daytime', 'nighttime' or 'both'"
    )
