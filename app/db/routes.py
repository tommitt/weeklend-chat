from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.db.schemas import (
    Conversation,
    ConversationInDb,
    Event,
    EventInDb,
    User,
    UserInDB,
)
from app.db.services import register_conversation, register_event, register_user

db_router = APIRouter()


@db_router.post("/register_new_user", response_model=UserInDB)
async def register_new_user(user_in: User, db: Session = Depends(get_db)):
    db_user = register_user(db=db, user_in=user_in)
    return db_user


@db_router.post("/register_new_conversation", response_model=ConversationInDb)
async def register_new_conversation(
    conversation_in: Conversation, db: Session = Depends(get_db)
):
    db_conversation = register_conversation(db=db, conversation_in=conversation_in)
    return db_conversation


@db_router.post("/register_new_event", response_model=EventInDb)
async def register_new_event(
    event_in: Event, source: str, db: Session = Depends(get_db)
):
    db_event = register_event(db=db, event_in=event_in, source=source)
    return db_event
