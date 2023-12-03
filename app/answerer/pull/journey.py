import datetime

from sqlalchemy.orm import Session

from app.answerer.pull.agent import AiAgent
from app.answerer.pull.messages import MESSAGE_NOT_DELIVERED, MESSAGE_WELCOME
from app.answerer.schemas import AnswerOutput, MessageInput
from app.constants import (
    CONVERSATION_HOURS_WINDOW,
    CONVERSATION_MAX_MESSAGES,
    THRESHOLD_NOT_DELIVERED_ANSWER,
)
from app.db.enums import AnswerType
from app.db.models import BusinessConversationORM, BusinessORM
from app.db.schemas import Business
from app.db.services import get_business, get_user_conversations, register_business
from app.utils.conversation_utils import db_to_langchain_conversation


class BusinessJourney:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _new_business_journey(
        self, phone_number: str
    ) -> tuple[AnswerOutput, BusinessORM]:
        db_user = register_business(
            db=self.db, user_in=Business(phone_number=phone_number)
        )
        output = AnswerOutput(answer=MESSAGE_WELCOME, type=AnswerType.template)
        return output, db_user

    def _get_previous_conversation(self, user_id: int) -> list[tuple[str, str]]:
        db_conversations = get_user_conversations(
            db=self.db,
            user_id=user_id,
            from_datetime=(
                datetime.datetime.now()
                - datetime.timedelta(hours=CONVERSATION_HOURS_WINDOW)
            ),
            orm=BusinessConversationORM,
            max_messages=CONVERSATION_MAX_MESSAGES,
        )
        return db_to_langchain_conversation(db_conversations)

    def _standard_business_journey(
        self, db_user: BusinessORM, user_query: str
    ) -> AnswerOutput:
        agent = AiAgent(db=self.db, db_business=db_user)
        output = agent.run(
            user_query,
            previous_conversation=self._get_previous_conversation(user_id=db_user.id),
        )
        return output

    def run(self, message: MessageInput) -> AnswerOutput:
        current_timestamp = int(datetime.datetime.utcnow().timestamp())

        db_user = get_business(self.db, phone_number=message.phone_number)
        if db_user is None:
            output, db_user = self._new_business_journey(
                phone_number=message.phone_number
            )
        else:
            if current_timestamp - message.timestamp > THRESHOLD_NOT_DELIVERED_ANSWER:
                output = AnswerOutput(
                    answer=MESSAGE_NOT_DELIVERED, type=AnswerType.failed
                )
            else:
                output = self._standard_business_journey(
                    db_user=db_user, user_query=message.body
                )
        output.user_id = db_user.id
        return output
