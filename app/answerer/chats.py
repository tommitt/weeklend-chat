from enum import Enum

from sqlalchemy.orm import Session

from app.answerer.pull import BusinessJourney
from app.answerer.push import UserJourney
from app.constants import WHATSAPP_PULL_NUMBER_ID, WHATSAPP_PUSH_NUMBER_ID
from app.db.models import BusinessConversationORM, BusinessORM, ConversationORM, UserORM


class ChatType(str, Enum):
    push = "push"
    pull = "pull"


class Chat:
    chat_type: ChatType
    wa_number_id: str
    user_orm: type[UserORM] | type[BusinessORM]
    conversation_orm: type[ConversationORM] | type[BusinessConversationORM]
    user_journey: UserJourney | BusinessJourney

    def __init__(self, wa_number_id: str, db: Session | None = None) -> None:
        self.wa_number_id = wa_number_id

        if self.wa_number_id == WHATSAPP_PUSH_NUMBER_ID:
            self.chat_type = ChatType.push
            self.user_orm = UserORM
            self.conversation_orm = ConversationORM
            self.user_journey = UserJourney(db=db)

        elif self.wa_number_id == WHATSAPP_PULL_NUMBER_ID:
            self.chat_type = ChatType.pull
            self.user_orm = BusinessORM
            self.conversation_orm = BusinessConversationORM
            self.user_journey = BusinessJourney(db=db)

        else:
            raise Exception(
                f"Cannot accept chat with WhatsApp number ID: {self.wa_number_id}."
            )
