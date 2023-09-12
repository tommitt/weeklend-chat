import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.enums import AnswerType
from app.db.models import ConversationORM, EventORM, UserORM
from app.db.schemas import Conversation, Event, User


def get_user(db: Session, phone_number: str) -> UserORM | None:
    return db.query(UserORM).filter(UserORM.phone_number == phone_number).first()


def get_user_count(db: Session) -> int:
    return db.query(func.count(UserORM.id)).scalar()


def get_user_answers_count(
    db: Session,
    user_id: int,
    answer_type: AnswerType | None,
    datetime_limit: datetime.datetime | None,
) -> int:
    return (
        db.query(func.count(ConversationORM.id))
        .filter(
            ConversationORM.user_id == user_id,
            (
                ConversationORM.registered_at >= datetime_limit
                if datetime_limit is not None
                else True
            ),
            (
                ConversationORM.answer_type == answer_type
                if answer_type is not None
                else True
            ),
        )
        .scalar()
    )


def register_user(user_in: User, db: Session) -> UserORM:
    db_user = get_user(db, phone_number=user_in.phone_number)
    if db_user:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    user_dict = user_in.dict()
    user_dict["registered_at"] = datetime.datetime.utcnow()

    db_user = UserORM(**user_dict)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def register_conversation(
    conversation_in: Conversation, db: Session
) -> ConversationORM:
    conversation_dict = conversation_in.dict()
    conversation_dict["registered_at"] = datetime.datetime.utcnow()

    db_conversation = ConversationORM(**conversation_dict)
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation


def register_event(event_in: Event, db: Session) -> EventORM:
    event_dict = event_in.dict()
    event_dict["registered_at"] = datetime.datetime.utcnow()

    db_event = EventORM(**event_dict)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event
