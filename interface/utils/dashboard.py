import datetime

import pandas as pd
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.constants import FAKE_USER_ID
from app.db.enums import AnswerType
from app.db.models import ClickORM, ConversationORM, EventORM, UserORM
from interface.utils.schemas import DashboardOutput


def get_dashboard_stats(
    db: Session, start_date: datetime.date, end_date: datetime.date
) -> DashboardOutput:
    start_dt = datetime.datetime.combine(start_date, datetime.time.min)
    end_dt = datetime.datetime.combine(
        end_date + datetime.timedelta(days=1), datetime.time.min
    )

    new_user_count = (
        db.query(func.count(distinct(UserORM.id)))
        .filter(
            UserORM.registered_at.between(start_dt, end_dt),
            UserORM.id != FAKE_USER_ID,
        )
        .scalar()
    )

    clicks_count = (
        db.query(func.count(distinct(ClickORM.id)))
        .filter(
            ClickORM.registered_at.between(start_dt, end_dt),
        )
        .scalar()
    )

    conversations_query = db.query(
        ConversationORM.user_id,
        ConversationORM.answer_type,
        ConversationORM.received_at,
        ConversationORM.registered_at,
    ).filter(ConversationORM.received_at.between(start_dt, end_dt))

    df_all = pd.DataFrame(
        conversations_query,
        columns=["user_id", "answer_type", "received_at", "registered_at"],
    )
    messages_count = df_all.shape[0]

    mask_fake_user = df_all["user_id"] == FAKE_USER_ID
    df = df_all[~mask_fake_user]

    users_count = len(df["user_id"].unique())

    mask_ai = df["answer_type"] == AnswerType.ai
    mask_blocked = df["answer_type"] == AnswerType.blocked
    mask_conversational = df["answer_type"] == AnswerType.conversational
    mask_failed = df["answer_type"] == AnswerType.failed
    mask_template = df["answer_type"] == AnswerType.template
    mask_unanswered = df["answer_type"] == AnswerType.unanswered

    avg_answer_time = (
        0
        if df.empty
        else (
            df[mask_ai]["registered_at"] - df[mask_ai]["received_at"]
        ).dt.seconds.mean()
    )

    uploaded_events_per_source = (
        db.query(EventORM.source, func.count().label("total_count"))
        .filter(EventORM.registered_at.between(start_dt, end_dt))
        .group_by(EventORM.source)
        .all()
    )

    active_events_per_source = (
        db.query(EventORM.source, func.count().label("total_count"))
        .filter(EventORM.start_date <= end_dt, EventORM.end_date >= start_dt)
        .group_by(EventORM.source)
        .all()
    )

    return DashboardOutput(
        users=users_count,
        users_new=new_user_count,
        users_recurring=users_count - new_user_count,
        conversations=messages_count,
        conversations_answered=(
            sum(mask_ai)
            + sum(mask_conversational)
            + sum(mask_template)
            + sum(mask_blocked)
        ),
        conversations_answered_ai=sum(mask_ai),
        conversations_answered_conversational=sum(mask_conversational),
        conversations_answered_welcome_template=new_user_count,
        conversations_answered_other_template=(sum(mask_template) - new_user_count),
        conversations_answered_blocked=sum(mask_blocked),
        conversations_unanswered=sum(mask_unanswered),
        conversations_failed=sum(mask_fake_user) + sum(mask_failed),
        clicks=clicks_count,
        avg_messages_per_user=messages_count / users_count if users_count > 0 else 0,
        avg_answer_time=avg_answer_time,
        uploaded_events={
            "Source": [r.source for r in uploaded_events_per_source],
            "# Events": [r.total_count for r in uploaded_events_per_source],
        },
        active_events={
            "Source": [r.source for r in active_events_per_source],
            "# Events": [r.total_count for r in active_events_per_source],
        },
    )
