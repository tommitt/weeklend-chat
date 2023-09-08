import datetime

from pydantic import BaseModel

from app.db.enums import CityEnum


class User(BaseModel):
    phone_number: str


class UserInDB(User):
    id: int
    registered_at: datetime.datetime

    class Config:
        orm_mode = True


class Conversation(BaseModel):
    user_id: int
    from_message: str
    to_message: str
    is_blocked: bool
    used_event_ids: str
    received_at: datetime.datetime


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

    # additional info
    location: str
    url: str
    opening_time: str
    closing_time: str


class EventInDb(Event):
    id: int
    registered_at: datetime.datetime

    class Config:
        orm_mode = True


class WebhookPayload(BaseModel):
    entry: list
    object: str
