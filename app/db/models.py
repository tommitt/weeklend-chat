import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.db import Base
from app.db.enums import AnswerType, BusinessType, CityEnum, PriceLevel


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(index=True)
    is_blocked: Mapped[bool]
    block_expires_at: Mapped[Optional[datetime.datetime]]
    is_admin: Mapped[bool]
    registered_at: Mapped[datetime.datetime]

    # relationships
    conversations: Mapped[list["ConversationORM"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"UserORM(id={self.id!r}, phone_number={self.phone_number!r})"


# TODO: create migration
class BusinessORM(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str]
    name: Mapped[Optional[str]]
    description: Mapped[Optional[str]]
    business_type: Mapped[Optional[BusinessType]]
    registered_at: Mapped[datetime.datetime]

    # relationships
    conversations: Mapped[list["BusinessConversationORM"]] = relationship(
        back_populates="user"
    )
    events: Mapped[list["EventORM"]] = relationship(back_populates="business")

    def __repr__(self) -> str:
        return f"BusinessORM(id={self.id!r}, phone_number={self.phone_number!r})"


class BaseConversation:
    id: Mapped[int] = mapped_column(primary_key=True)
    wa_id: Mapped[str] = mapped_column(index=True)  # format: "wamid.ID"
    from_message: Mapped[str]
    to_message: Mapped[Optional[str]]
    answer_type: Mapped[AnswerType]
    used_event_ids: Mapped[str]  # json.dumps(list[ForeignKey("events.id")]))
    received_at: Mapped[datetime.datetime]
    registered_at: Mapped[datetime.datetime]


class ConversationORM(Base, BaseConversation):
    __tablename__ = "conversations"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # relationships
    user: Mapped["UserORM"] = relationship(back_populates="conversations")

    def __repr__(self) -> str:
        return f"ConversationORM(id={self.id!r}, from_id={self.user_id!r}, at={self.registered_at!r})"


class BusinessConversationORM(Base, BaseConversation):
    __tablename__ = "business_conversations"

    user_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"))
    # relationships
    user: Mapped["BusinessORM"] = relationship(back_populates="conversations")

    def __repr__(self) -> str:
        return f"BusinessConversationORM(id={self.id!r}, from_id={self.user_id!r}, at={self.registered_at!r})"


class EventORM(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str]
    is_vectorized: Mapped[bool]
    source: Mapped[str]
    business_id: Mapped[Optional[int]] = mapped_column(ForeignKey("businesses.id"))
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
    is_for_children: Mapped[bool]
    is_for_disabled: Mapped[bool]
    is_for_animals: Mapped[bool]

    # additional info
    name: Mapped[Optional[str]]
    location: Mapped[Optional[str]]
    url: Mapped[Optional[str]]
    price_level: Mapped[Optional[PriceLevel]]

    # relationships
    business: Mapped["BusinessORM"] = relationship(back_populates="events")

    def __repr__(self) -> str:
        return f"EventORM(id={self.id!r})"
