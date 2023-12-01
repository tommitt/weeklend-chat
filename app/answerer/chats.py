from enum import Enum

from sqlalchemy.orm import Session

from app.answerer.push.journey import UserJourney
from app.constants import WHATSAPP_PULL_NUMBER_ID, WHATSAPP_PUSH_NUMBER_ID
from app.db.models import BusinessConversationORM, BusinessORM, ConversationORM, UserORM


class ChatType(str, Enum):
    push = "push"
    pull = "pull"


class Chat:
    whatsapp_number_id: str
    user_orm: type[UserORM] | type[BusinessORM]
    conversation_orm: type[ConversationORM] | type[BusinessConversationORM]
    # TODO: add business journey
    user_journey: UserJourney | None = None

    def __init__(self, chat_type: ChatType, db: Session | None = None) -> None:
        if chat_type == ChatType.push:
            self.whatsapp_number_id = WHATSAPP_PUSH_NUMBER_ID
            self.user_orm = UserORM
            self.conversation_orm = ConversationORM
            if db is not None:
                self.user_journey = UserJourney(db=db)

        elif chat_type == ChatType.pull:
            self.whatsapp_number_id = WHATSAPP_PULL_NUMBER_ID
            self.user_orm = BusinessORM
            self.conversation_orm = BusinessConversationORM

        else:
            raise Exception(f"Chat type {chat_type} not accepted.")
