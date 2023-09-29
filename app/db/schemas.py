import datetime

from pydantic import BaseModel

from app.db.enums import AnswerType, CityEnum
from app.db.models import EventORM
from app.utils.datetime_utils import date_to_timestamp


class User(BaseModel):
    phone_number: str
    is_blocked: bool
    block_expires_at: datetime.datetime | None = None
    is_admin: bool = False


class UserInDB(User):
    id: int
    registered_at: datetime.datetime

    class Config:
        orm_mode = True


class ConversationTemp(BaseModel):
    from_message: str
    wa_id: str
    received_at: datetime.datetime


class ConversationUpd(BaseModel):
    user_id: int
    to_message: str | None
    answer_type: AnswerType
    used_event_ids: str


class Conversation(ConversationTemp, ConversationUpd):
    pass


class ConversationInDb(Conversation):
    id: int
    registered_at: datetime.datetime

    class Config:
        orm_mode = True


class Event(BaseModel):
    description: str
    is_vectorized: bool

    # metadata
    city: CityEnum
    start_date: datetime.date
    end_date: datetime.date
    is_closed_mon: bool
    is_closed_tue: bool
    is_closed_wed: bool
    is_closed_thu: bool
    is_closed_fri: bool
    is_closed_sat: bool
    is_closed_sun: bool
    is_during_day: bool
    is_during_night: bool
    is_countryside: bool
    is_for_children: bool
    is_for_disabled: bool
    is_for_animals: bool

    # additional info
    name: str | None
    location: str | None
    url: str | None


class EventInDb(Event):
    id: int
    source: str
    registered_at: datetime.datetime

    class Config:
        orm_mode = True


class EventInVectorstore(BaseModel):
    id: int
    source: str

    # metadata
    city: CityEnum
    start_date: datetime.date | int
    end_date: datetime.date | int
    is_closed_mon: bool
    is_closed_tue: bool
    is_closed_wed: bool
    is_closed_thu: bool
    is_closed_fri: bool
    is_closed_sat: bool
    is_closed_sun: bool
    is_during_day: bool
    is_during_night: bool
    is_countryside: bool
    is_for_children: bool
    is_for_disabled: bool
    is_for_animals: bool

    class Config:
        orm_mode = True

    def from_event_orm(orm: EventORM) -> "EventInVectorstore":
        event = EventInVectorstore.from_orm(orm)

        # convert datetime to int
        event.start_date = date_to_timestamp(event.start_date)
        event.end_date = date_to_timestamp(event.end_date)

        return event


class WebhookPayload(BaseModel):
    entry: list
    object: str


class AnswerOutput(BaseModel):
    answer: str | None
    type: AnswerType
    used_event_ids: list[int] | None = None
