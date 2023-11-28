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
from app.answerer.schemas import AnswerOutput
from app.constants import (
    CONVERSATION_HOURS_WINDOW,
    CONVERSATION_MAX_MESSAGES,
    LIMIT_ANSWERS_PER_WEEK,
    LIMIT_BLOCKS_PER_WEEK,
    LIMIT_MAX_USERS,
    THRESHOLD_NOT_DELIVERED_ANSWER,
)
from app.db.enums import AnswerType
from app.db.models import UserORM
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


def blocked_user_journey(db: Session, db_user: UserORM) -> AnswerOutput:
    if (
        db_user.block_expires_at is not None
        and db_user.block_expires_at < datetime.datetime.utcnow()
    ):
        db_user = unblock_user(db=db, db_user=db_user)
        return AnswerOutput(answer=MESSAGE_GOT_UNBLOCKED, type=AnswerType.template)

    return AnswerOutput(answer=None, type=AnswerType.unanswered)


def new_user_journey(db: Session, phone_number: str) -> tuple[AnswerOutput, UserORM]:
    num_users = get_user_count(db=db)
    if num_users > LIMIT_MAX_USERS:
        new_user_answer = MESSAGE_REACHED_MAX_USERS
        is_blocked = True
    else:
        new_user_answer = MESSAGE_WELCOME
        is_blocked = False

    db_user = register_user(
        db=db, user_in=User(phone_number=phone_number, is_blocked=is_blocked)
    )
    output = AnswerOutput(answer=new_user_answer, type=AnswerType.template)

    return output, db_user


def check_user_limit_by_answertype(
    db: Session,
    db_user: UserORM,
    answer_type: AnswerType,
    timedelta: datetime.timedelta,
    limit: int,
    block_message: str,
) -> AnswerOutput | None:
    count, first_datetime = get_user_answers_count(
        db=db,
        user_id=db_user.id,
        answer_type=answer_type,
        datetime_limit=(datetime.datetime.utcnow() - timedelta),
    )

    if count >= limit:
        block_expires_at = first_datetime + timedelta
        db_user = block_user(db=db, db_user=db_user, block_expires_at=block_expires_at)
        return AnswerOutput(
            answer=block_message.format(
                limit_per_week=limit,
                block_expires_at=block_expires_at.strftime("%d/%m/%Y"),
            ),
            type=AnswerType.template,
        )

    return None


def check_user_limits(db: Session, db_user: UserORM) -> AnswerOutput | None:
    timedelta = datetime.timedelta(days=7)

    output = check_user_limit_by_answertype(
        db=db,
        db_user=db_user,
        answer_type=AnswerType.ai,
        timedelta=timedelta,
        limit=LIMIT_ANSWERS_PER_WEEK,
        block_message=MESSAGE_WEEK_ANSWERS_LIMIT,
    )
    if output is not None:
        return output

    output = check_user_limit_by_answertype(
        db=db,
        db_user=db_user,
        answer_type=AnswerType.blocked,
        timedelta=timedelta,
        limit=LIMIT_BLOCKS_PER_WEEK,
        block_message=MESSAGE_WEEK_BLOCKS_LIMIT,
    )
    if output is not None:
        return output

    return None


def get_previous_conversation(db: Session, user_id: int) -> list[tuple[str, str]]:
    db_conversations = get_user_conversations(
        db=db,
        user_id=user_id,
        from_datetime=(
            datetime.datetime.now()
            - datetime.timedelta(hours=CONVERSATION_HOURS_WINDOW)
        ),
        max_messages=CONVERSATION_MAX_MESSAGES,
    )
    llm_conversations = []
    for db_conversation in db_conversations:
        llm_conversations.append(("human", db_conversation.from_message))
        if db_conversation.answer_type != AnswerType.unanswered:
            llm_conversations.append(("ai", db_conversation.to_message))
    return llm_conversations


def standard_user_journey(
    db: Session, db_user: UserORM, user_query: str
) -> AnswerOutput:
    output = check_user_limits(db=db, db_user=db_user) if not db_user.is_admin else None

    if output is None:
        agent = AiAgent(db=db)
        output = agent.run(
            user_query,
            previous_conversation=get_previous_conversation(db=db, user_id=db_user.id),
        )

    return output


def user_journey(
    db: Session,
    phone_number: str,
    user_query: str,
    message_timestamp: int,
) -> tuple[AnswerOutput, int]:
    current_timestamp = int(datetime.datetime.utcnow().timestamp())

    db_user = get_user(db, phone_number=phone_number)
    if db_user is None:
        output, db_user = new_user_journey(db=db, phone_number=phone_number)
    else:
        if db_user.is_blocked:
            output = blocked_user_journey(db=db, db_user=db_user)
        elif current_timestamp - message_timestamp > THRESHOLD_NOT_DELIVERED_ANSWER:
            output = AnswerOutput(answer=MESSAGE_NOT_DELIVERED, type=AnswerType.failed)
        else:
            output = standard_user_journey(
                db=db, db_user=db_user, user_query=user_query
            )
    return (output, db_user.id)
