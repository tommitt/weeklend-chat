import datetime

from sqlalchemy.orm import Session

from app.answerer.push.agent import AiAgent
from app.answerer.push.messages import (
    MESSAGE_GOT_UNBLOCKED,
    MESSAGE_NOT_DELIVERED,
    MESSAGE_REACHED_MAX_USERS,
    MESSAGE_WEEK_ANSWERS_LIMIT,
    MESSAGE_WEEK_BLOCKS_LIMIT,
    MESSAGE_WELCOME,
)
from app.answerer.schemas import AnswerOutput, MessageInput
from app.constants import (
    CONVERSATION_HOURS_WINDOW,
    CONVERSATION_MAX_MESSAGES,
    LIMIT_ANSWERS_PER_WEEK,
    LIMIT_BLOCKS_PER_WEEK,
    LIMIT_MAX_USERS,
    THRESHOLD_NOT_DELIVERED_ANSWER,
)
from app.db.enums import AnswerType
from app.db.models import ConversationORM, UserORM
from app.db.schemas import User
from app.db.services import (
    block_user,
    get_user,
    get_user_answers_count,
    get_user_conversations,
    get_user_count,
    register_user,
    unblock_user,
)
from app.utils.conversation_utils import db_to_langchain_conversation


class UserJourney:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _blocked_user_journey(self, db_user: UserORM) -> AnswerOutput:
        if (
            db_user.block_expires_at is not None
            and db_user.block_expires_at < datetime.datetime.utcnow()
        ):
            db_user = unblock_user(db=self.db, db_user=db_user)
            return AnswerOutput(answer=MESSAGE_GOT_UNBLOCKED, type=AnswerType.template)

        return AnswerOutput(answer=None, type=AnswerType.unanswered)

    def _new_user_journey(self, phone_number: str) -> tuple[AnswerOutput, UserORM]:
        num_users = get_user_count(db=self.db)
        if num_users > LIMIT_MAX_USERS:
            new_user_answer = MESSAGE_REACHED_MAX_USERS
            is_blocked = True
        else:
            new_user_answer = MESSAGE_WELCOME
            is_blocked = False

        db_user = register_user(
            db=self.db, user_in=User(phone_number=phone_number, is_blocked=is_blocked)
        )
        output = AnswerOutput(answer=new_user_answer, type=AnswerType.template)

        return output, db_user

    def _check_user_limit_by_answertype(
        self,
        db_user: UserORM,
        answer_type: AnswerType,
        timedelta: datetime.timedelta,
        limit: int,
        block_message: str,
    ) -> AnswerOutput | None:
        count, first_datetime = get_user_answers_count(
            db=self.db,
            user_id=db_user.id,
            answer_type=answer_type,
            datetime_limit=(datetime.datetime.utcnow() - timedelta),
        )

        if count >= limit:
            block_expires_at = first_datetime + timedelta
            db_user = block_user(
                db=self.db, db_user=db_user, block_expires_at=block_expires_at
            )
            return AnswerOutput(
                answer=block_message.format(
                    limit_per_week=limit,
                    block_expires_at=block_expires_at.strftime("%d/%m/%Y"),
                ),
                type=AnswerType.template,
            )

        return None

    def _check_user_limits(self, db_user: UserORM) -> AnswerOutput | None:
        timedelta = datetime.timedelta(days=7)

        output = self._check_user_limit_by_answertype(
            db_user=db_user,
            answer_type=AnswerType.ai,
            timedelta=timedelta,
            limit=LIMIT_ANSWERS_PER_WEEK,
            block_message=MESSAGE_WEEK_ANSWERS_LIMIT,
        )
        if output is not None:
            return output

        output = self._check_user_limit_by_answertype(
            db_user=db_user,
            answer_type=AnswerType.blocked,
            timedelta=timedelta,
            limit=LIMIT_BLOCKS_PER_WEEK,
            block_message=MESSAGE_WEEK_BLOCKS_LIMIT,
        )
        if output is not None:
            return output

        return None

    def _get_previous_conversation(self, user_id: int) -> list[tuple[str, str]]:
        db_conversations = get_user_conversations(
            db=self.db,
            user_id=user_id,
            from_datetime=(
                datetime.datetime.now()
                - datetime.timedelta(hours=CONVERSATION_HOURS_WINDOW)
            ),
            orm=ConversationORM,
            max_messages=CONVERSATION_MAX_MESSAGES,
        )
        return db_to_langchain_conversation(db_conversations)

    def _standard_user_journey(self, db_user: UserORM, user_query: str) -> AnswerOutput:
        output = (
            self._check_user_limits(db_user=db_user) if not db_user.is_admin else None
        )

        if output is None:
            agent = AiAgent(db=self.db)
            output = agent.run(
                user_query,
                previous_conversation=self._get_previous_conversation(db_user.id),
            )

        return output

    def run(self, message: MessageInput) -> AnswerOutput:
        current_timestamp = int(datetime.datetime.utcnow().timestamp())

        db_user = get_user(self.db, phone_number=message.phone_number)
        if db_user is None:
            output, db_user = self._new_user_journey(phone_number=message.phone_number)
        else:
            if db_user.is_blocked:
                output = self._blocked_user_journey(db_user=db_user)
            elif current_timestamp - message.timestamp > THRESHOLD_NOT_DELIVERED_ANSWER:
                output = AnswerOutput(
                    answer=MESSAGE_NOT_DELIVERED, type=AnswerType.failed
                )
            else:
                output = self._standard_user_journey(
                    db_user=db_user, user_query=message.body
                )
        output.user_id = db_user.id
        return output
