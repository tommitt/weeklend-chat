import datetime

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.constants import FAKE_USER_ID
from app.db.enums import AnswerType
from app.db.models import ConversationORM, UserORM
from app.db.schemas import DashboardOutput


def get_dashboard_stats(
    db: Session, start_date: datetime.date, end_date: datetime.date
) -> dict:
    start_dt = datetime.datetime.combine(start_date, datetime.time.min)
    end_dt = datetime.datetime.combine(
        end_date + datetime.timedelta(days=1), datetime.time.min
    )

    users_count = (
        db.query(func.count(distinct(ConversationORM.user_id)))
        .filter(
            ConversationORM.received_at.between(start_dt, end_dt),
            ConversationORM.user_id != FAKE_USER_ID,
        )
        .scalar()
    )

    convs_count_by_type = (
        db.query(ConversationORM.answer_type, func.count())
        .filter(
            ConversationORM.received_at.between(start_dt, end_dt),
            ConversationORM.user_id != FAKE_USER_ID,
        )
        .group_by(ConversationORM.answer_type)
        .all()
    )

    new_user_count = (
        db.query(func.count(distinct(UserORM.id)))
        .filter(
            UserORM.registered_at.between(start_dt, end_dt),
            UserORM.id != FAKE_USER_ID,
        )
        .scalar()
    )

    failed_convs_count = (
        db.query(func.count(ConversationORM.id))
        .filter(
            ConversationORM.received_at.between(start_dt, end_dt),
            ConversationORM.user_id == FAKE_USER_ID,
        )
        .scalar()
    )

    answers_ai_count = next(
        (v for k, v in convs_count_by_type if k == AnswerType.ai), 0
    )
    answers_template_count = next(
        (v for k, v in convs_count_by_type if k == AnswerType.template), 0
    )
    answers_blocked_count = next(
        (v for k, v in convs_count_by_type if k == AnswerType.blocked), 0
    )
    answers_unanswered_count = next(
        (v for k, v in convs_count_by_type if k == AnswerType.unanswered), 0
    )

    convs_tot_count = (
        answers_ai_count
        + answers_template_count
        + answers_blocked_count
        + answers_unanswered_count
        + failed_convs_count
    )

    return DashboardOutput(
        users=users_count,
        users_new=new_user_count,
        users_recurring=users_count - new_user_count,
        conversations=convs_tot_count,
        conversations_answered=(
            answers_ai_count + answers_template_count + answers_blocked_count
        ),
        conversations_answered_ai=answers_ai_count,
        conversations_answered_welcome_template=new_user_count,
        conversations_answered_other_template=(answers_template_count - new_user_count),
        conversations_answered_blocked=answers_blocked_count,
        conversations_unanswered=answers_unanswered_count,
        conversations_failed=failed_convs_count,
        avg_messages_per_user=convs_tot_count / users_count,
    )
