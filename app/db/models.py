import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.db import Base
from app.db.enums import AnswerType, CityEnum


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(index=True)
    is_blocked: Mapped[bool]
    registered_at: Mapped[datetime.datetime]

    conversations: Mapped[list["ConversationORM"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"UserORM(id={self.id!r}, phone_number={self.phone_number!r})"


class ConversationORM(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    from_message: Mapped[str]
    to_message: Mapped[Optional[str]]
    answer_type: Mapped[AnswerType]
    used_event_ids: Mapped[str]  # json.dumps(list[ForeignKey("events.id")]))
    received_at: Mapped[datetime.datetime]
    registered_at: Mapped[datetime.datetime]

    user: Mapped["UserORM"] = relationship(back_populates="conversations")

    def __repr__(self) -> str:
        return f"ConversationORM(id={self.id!r}, from_id={self.user_id}, at={self.registered_at})"


class EventORM(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str]
    is_vectorized: Mapped[bool]
    registered_at: Mapped[datetime.datetime]

    # metadata
    city: Mapped[CityEnum]
    start_date: Mapped[datetime.date]
    end_date: Mapped[datetime.date]
    is_closed_mon: Mapped[bool]
    is_closed_tue: Mapped[bool]
    is_closed_wed: Mapped[bool]
    is_closed_thu: Mapped[bool]
    is_closed_fri: Mapped[bool]
    is_closed_sat: Mapped[bool]
    is_closed_sun: Mapped[bool]
    is_during_day: Mapped[bool]
    is_during_night: Mapped[bool]
    is_countryside: Mapped[bool]
    is_for_children: Mapped[Optional[bool]]
    is_for_disabled: Mapped[Optional[bool]]
    is_for_animals: Mapped[Optional[bool]]

    # additional info
    name: Mapped[str]
    location: Mapped[Optional[str]]
    url: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"EventORM(id={self.id!r})"
