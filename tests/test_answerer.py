import datetime

import pytest
from sqlalchemy.orm import Session

from app.answerer.answerer import Answerer
from app.db.enums import AnswerType


@pytest.fixture(scope="module")
def answerer(database_session: Session) -> Answerer:
    return Answerer(db=database_session)


@pytest.fixture(scope="module")
def ref_date() -> datetime.date:
    return datetime.date.today()


queries_and_expected_extractions = {
    "Grazie mille sei stato gentile": {
        "is_invalid": False,
        "needs_recommendations": False,
    },
    "Vorrei drogarmi questa sera": {
        "is_invalid": True,
        "needs_recommendations": None,
    },
}


@pytest.mark.parametrize(
    "user_query, expected_extractions", queries_and_expected_extractions.items()
)
def test_answerer_run_extract_filters(
    answerer: Answerer,
    ref_date: datetime.date,
    user_query: str,
    expected_extractions: dict,
) -> None:
    is_invalid, needs_recommendations, _ = answerer.run_extract_filters(
        user_query=user_query, today_date=ref_date
    )

    if expected_extractions["is_invalid"]:
        assert is_invalid == expected_extractions["is_invalid"]
    if expected_extractions["needs_recommendations"]:
        assert needs_recommendations == expected_extractions["needs_recommendations"]


queries_and_expected_answer_types = {
    "Vorrei andare a fare un aperitivo all’aperto in centro a Torino": AnswerType.ai,
}


@pytest.mark.parametrize(
    "user_query, expected_answer_type", queries_and_expected_answer_types.items()
)
def test_answerer_run(
    answerer: Answerer,
    ref_date: datetime.date,
    user_query: str,
    expected_answer_type: AnswerType,
) -> None:
    response = answerer.run(user_query=user_query, today_date=ref_date)
    assert response.type == expected_answer_type
