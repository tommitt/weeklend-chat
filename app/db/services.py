import datetime

import pinecone
from fastapi import HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.constants import (
    EMBEDDING_SIZE,
    FAKE_USER_ID,
    PINECONE_API_KEY,
    PINECONE_ENV,
    PINECONE_INDEX,
    PINECONE_NAMESPACE,
)
from app.db.enums import AnswerType
from app.db.models import (
    BusinessConversationORM,
    BusinessORM,
    ClickORM,
    ConversationORM,
    EventORM,
    UserORM,
)
from app.db.schemas import (
    Business,
    Click,
    Conversation,
    ConversationTemp,
    ConversationUpd,
    Event,
    User,
)


# User
def get_user_by_id(
    db: Session, id: int, orm: type[UserORM] | type[BusinessORM]
) -> UserORM | BusinessORM | None:
    return db.query(orm).filter_by(id=id).first()


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


def set_admin_user(db: Session, db_user: UserORM) -> UserORM:
    if db_user.is_blocked:
        db_user = unblock_user(db=db, db_user=db_user)
    db_user.is_admin = True
    db.commit()
    return db_user


def register_user(db: Session, user_in: User) -> UserORM:
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


# Business
def get_business(db: Session, phone_number: str) -> BusinessORM | None:
    return (
        db.query(BusinessORM).filter(BusinessORM.phone_number == phone_number).first()
    )


def update_business_info(
    db: Session, business_id: int, name: str, description: str
) -> BusinessORM:
    db_business = get_user_by_id(db=db, id=business_id, orm=BusinessORM)
    db_business.name = name
    db_business.description = description
    db.commit()
    return db_business


def register_business(db: Session, business_in: Business) -> BusinessORM:
    db_business = get_business(db, phone_number=business_in.phone_number)
    if db_business:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    business_dict = business_in.dict()
    business_dict["registered_at"] = datetime.datetime.utcnow()

    db_business = BusinessORM(**business_dict)
    db.add(db_business)
    db.commit()
    db.refresh(db_business)
    return db_business


# Conversation
def get_conversation_by_waid(
    db: Session, wa_id: str, orm: type[ConversationORM] | type[BusinessConversationORM]
) -> ConversationORM | BusinessConversationORM | None:
    """Get single conversation from the WhatsApp ID."""
    return db.query(orm).filter(orm.wa_id == wa_id).first()


def get_user_conversations(
    db: Session,
    user_id: int,
    from_datetime: datetime.datetime | None,
    orm: type[ConversationORM] | type[BusinessConversationORM],
    max_messages: int = 100,
) -> list[ConversationORM | BusinessConversationORM]:
    """
    Get last conversations of a user from a certain datetime.
    Conversations are returned ordered from the oldest to the newest.
    """
    return (
        db.query(orm)
        .filter(
            orm.user_id == user_id,
            (orm.registered_at >= from_datetime if from_datetime is not None else True),
        )
        .order_by(desc(orm.id))
        .limit(max_messages)
        .all()
    )[::-1]


def register_conversation(
    db: Session,
    conversation_in: Conversation,
    orm: type[ConversationORM] | type[BusinessConversationORM],
) -> ConversationORM | BusinessConversationORM:
    conversation_dict = conversation_in.dict()
    conversation_dict["registered_at"] = datetime.datetime.utcnow()

    db_conversation = orm(**conversation_dict)
    db.add(db_conversation)
    db.commit()
    db.refresh(db_conversation)
    return db_conversation


def register_temp_conversation(
    db: Session,
    conversation_temp_in: ConversationTemp,
    user_orm: type[UserORM] | type[BusinessORM],
    conversation_orm: type[ConversationORM] | type[BusinessConversationORM],
) -> ConversationORM | BusinessConversationORM:
    """
    Conversation is registered temporarily with no answer to avoid
    accepting a request with the same message while it is being processed.
    """
    fake_user = get_user_by_id(db=db, id=FAKE_USER_ID, orm=user_orm)
    if fake_user is None:
        if user_orm == UserORM:
            fake_user = UserORM(
                id=FAKE_USER_ID,
                phone_number="000000000000",
                is_blocked=False,
                is_admin=False,
                registered_at=datetime.datetime.utcnow(),
            )
        elif user_orm == BusinessORM:
            fake_user = BusinessORM(
                id=FAKE_USER_ID,
                phone_number="000000000000",
                registered_at=datetime.datetime.utcnow(),
            )
        else:
            raise Exception(f"User ORM of type {user_orm} is not accepted.")
        db.add(fake_user)
        db.commit()

    db_conversation = register_conversation(
        db=db,
        conversation_in=Conversation(
            from_message=conversation_temp_in.from_message,
            wa_id=conversation_temp_in.wa_id,
            received_at=conversation_temp_in.received_at,
            # temporary values ->
            user_id=FAKE_USER_ID,
            to_message=None,
            answer_type=AnswerType.unanswered,
            used_event_ids="null",
        ),
        orm=conversation_orm,
    )
    return db_conversation


def update_temp_conversation(
    db: Session,
    db_conversation: ConversationORM | BusinessConversationORM,
    conversation_update_in: ConversationUpd,
) -> ConversationORM | BusinessConversationORM:
    for attr_name, attr_value in vars(conversation_update_in).items():
        setattr(db_conversation, attr_name, attr_value)
    db.commit()
    return db_conversation


def delete_temp_conversation(
    db: Session, db_conversation: ConversationORM | BusinessConversationORM
) -> None:
    if db_conversation.user_id == FAKE_USER_ID:
        db.delete(db_conversation)
        db.commit()


# Event
def get_event_by_id(db: Session, id: int) -> EventORM | None:
    return db.query(EventORM).filter_by(id=id).first()


def get_event(
    db: Session,
    source: str,
    url: str | None = None,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
) -> EventORM | None:
    return (
        db.query(EventORM)
        .filter(
            EventORM.source == source,
            EventORM.url == url if url is not None else True,
            EventORM.start_date == start_date if start_date is not None else True,
            EventORM.end_date == end_date if end_date is not None else True,
        )
        .first()
    )


def register_event(db: Session, event_in: Event, source: str) -> EventORM:
    event_dict = event_in.dict()
    event_dict["registered_at"] = datetime.datetime.utcnow()
    event_dict["source"] = source

    db_event = EventORM(**event_dict)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def delete_event_by_id(db: Session, event_id: int, from_vectorstore_only: bool = True):
    """
    Delete event by id from vectorstore and (optionally) from database.
    This implementation is Pinecone-specific.
    """
    db_event = get_event_by_id(db=db, id=event_id)

    if db_event is None:
        raise Exception(f"Event (id={event_id}) not present in database.")
    if not db_event.is_vectorized:
        raise Exception(f"Event (id={event_id}) is not vectorized.")

    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
    index = pinecone.Index(PINECONE_INDEX)

    queries = index.query(
        top_k=1,
        vector=[0] * EMBEDDING_SIZE,
        namespace=PINECONE_NAMESPACE,
        include_metadata=True,
        include_values=False,
        filter={"id": event_id},
    )
    doc_event = [q for q in queries["matches"]][0]
    delete_response = index.delete(ids=[doc_event.id], namespace=PINECONE_NAMESPACE)
    if delete_response:
        raise Exception(
            f"Pinecone failed to delete event (id={event_id}). Response: {delete_response}"
        )

    db_event.is_vectorized = False

    if not from_vectorstore_only:
        db.delete(db_event)

    db.commit()


# Click
def register_click(db: Session, click_in: Click) -> ClickORM:
    click_dict = click_in.dict()
    click_dict["registered_at"] = datetime.datetime.utcnow()

    db_click = ClickORM(**click_dict)
    db.add(db_click)
    db.commit()
    db.refresh(db_click)
    return db_click
