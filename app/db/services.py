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
) -> tuple[int, datetime.datetime | None]:
    return (
        db.query(func.count(), func.min(ConversationORM.registered_at))
        .select_from(ConversationORM)
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
    ).first()


def block_user(
    db: Session, db_user: UserORM, block_expires_at: datetime.datetime
) -> UserORM:
    if db_user.is_blocked:
        raise Exception("User is already blocked")
    db_user.is_blocked = True
    db_user.block_expires_at = block_expires_at
    db.commit()
    return db_user


def unblock_user(db: Session, db_user: UserORM) -> UserORM:
    if not db_user.is_blocked:
        raise Exception("User is already unblocked")
    db_user.is_blocked = False
    db_user.block_expires_at = None
    db.commit()
    return db_user


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


def get_conversation(db: Session, wa_id: str) -> ConversationORM | None:
    return db.query(ConversationORM).filter(ConversationORM.wa_id == wa_id).first()


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


def get_event_by_id(db: Session, id: int) -> EventORM | None:
    return db.query(EventORM).filter_by(id=id).first()


def get_event(db: Session, source: str, url: str | None) -> EventORM | None:
    return (
        db.query(EventORM)
        .filter(
            EventORM.source == source,
            EventORM.url == url if url is not None else True,
        )
        .first()
    )


def register_event(event_in: Event, source: str, db: Session) -> EventORM:
    event_dict = event_in.dict()
    event_dict["registered_at"] = datetime.datetime.utcnow()
    event_dict["source"] = source

    db_event = EventORM(**event_dict)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event
