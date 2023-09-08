from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import now

from app.db.models import ConversationORM, EventORM, UserORM
from app.db.schemas import Conversation, Event, User


def get_user(db: Session, phone_number: str) -> UserORM | None:
    return db.query(UserORM).filter(UserORM.phone_number == phone_number).first()


def register_user(user_in: User, db: Session) -> UserORM:
    db_user = get_user(db, phone_number=user_in.phone_number)
    if db_user:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    user_dict = user_in.dict()
    user_dict["registered_at"] = now()

    db_user = UserORM(**user_dict)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def register_conversation(
    conversation_in: Conversation, db: Session
) -> ConversationORM:
    conversation_dict = conversation_in.dict()
    conversation_dict["registered_at"] = now()

    db_conversation = ConversationORM(**conversation_dict)
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation


def register_event(event_in: Event, db: Session) -> EventORM:
    event_dict = event_in.dict()
    event_dict["registered_at"] = now()

    db_event = EventORM(**event_dict)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event
