import datetime

import pytest
from sqlalchemy.orm import Session

from app.answerer.push import AiAgent
from app.db.enums import AnswerType


@pytest.fixture(scope="module")
def ref_date() -> datetime.date:
    return datetime.date.today()


@pytest.fixture(scope="module")
def ai_agent(database_session: Session, ref_date: datetime.date) -> AiAgent:
    return AiAgent(db=database_session, today_date=ref_date)


queries_and_expected_answer_types = {
    "Ciao! Come puoi aiutarmi?": AnswerType.conversational,
    "Vorrei andare a fare un aperitivo all’aperto in centro a Torino": AnswerType.ai,
}


@pytest.mark.parametrize(
    "user_query, expected_answer_type", queries_and_expected_answer_types.items()
)
def test_agent_run(
    ai_agent: AiAgent,
    user_query: str,
    expected_answer_type: AnswerType,
) -> None:
    response = ai_agent.run(user_query=user_query)
    assert response.type == expected_answer_type
