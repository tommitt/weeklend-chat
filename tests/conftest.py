import pytest
from sqlalchemy.orm import Session

from app.db.db import SessionLocal


@pytest.fixture(scope="session")
def database_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
