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
from app.db.schemas import Business, BusinessInDB
from app.db.services import get_business, get_user_conversations, register_business
from app.utils.conversation_utils import db_to_langchain_conversation


class BusinessJourney:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _new_business_journey(
        self, phone_number: str
    ) -> tuple[AnswerOutput, BusinessORM]:
        db_user = register_business(
            db=self.db, business_in=Business(phone_number=phone_number)
        )
        output = AnswerOutput(answer=MESSAGE_WELCOME, type=AnswerType.template)
        return output, db_user

    def _standard_business_journey(
        self, db_user: BusinessORM, user_query: str
    ) -> AnswerOutput:
        agent = AiAgent(db=self.db, business=BusinessInDB.from_orm(db_user))

        db_conversations = get_user_conversations(
            db=self.db,
            user_id=db_user.id,
            from_datetime=(
                datetime.datetime.now()
                - datetime.timedelta(hours=CONVERSATION_HOURS_WINDOW)
            ),
            orm=BusinessConversationORM,
            max_messages=CONVERSATION_MAX_MESSAGES,
        )

        if (
            len(db_conversations) > 0
            and db_conversations[-1].answer_type == AnswerType.ai
        ):
            pending_event_id = db_conversations[-1].used_event_ids[0]
        else:
            pending_event_id = None

        output = agent.run(
            user_query,
            previous_conversation=db_to_langchain_conversation(db_conversations),
            pending_event_id=pending_event_id,
        )
        return output

    def run(self, message: MessageInput) -> tuple[AnswerOutput, int]:
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

        return (output, db_user.id)
