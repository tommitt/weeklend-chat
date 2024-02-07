import datetime

from pydantic import BaseModel

from app.db.schemas import BusinessInDB, UserInDB


class ChatbotInput(BaseModel):
    user_query: str
    today_date: datetime.date
    previous_conversation: list[tuple]
    user: UserInDB | BusinessInDB
    pending_event_id: int | None


class DashboardOutput(BaseModel):
    users: int
    users_new: int
    users_recurring: int

    conversations: int
    conversations_answered: int
    conversations_answered_ai: int
    conversations_answered_conversational: int
    conversations_answered_welcome_template: int
    conversations_answered_other_template: int
    conversations_answered_blocked: int
    conversations_unanswered: int
    conversations_failed: int

    clicks: int

    avg_messages_per_user: float
    median_answer_time: float

    uploaded_events: dict[str, list]
    active_events: dict[str, list]
