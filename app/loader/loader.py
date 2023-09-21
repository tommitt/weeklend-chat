from langchain.docstore.document import Document
from sqlalchemy.orm import Session

from app.db.models import EventORM
from app.db.schemas import EventInVectorDB
from app.utils.conn import get_vectorstore


class Loader:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.vectorstore = get_vectorstore()
        self.events: list[EventORM] = []

    def get_not_vectorized_events(self) -> None:
        query = self.db.query(EventORM).filter(EventORM.is_vectorized == False)
        self.events = [e for e in query]

    def vectorize_events(self) -> None:
        for event_orm in self.events:
            event_doc = Document(
                page_content=event_orm.description,
                metadata=EventInVectorDB.from_event_orm(event_orm).__dict__,
            )
            self.vectorstore.add_documents([event_doc])
            event_orm.is_vectorized = True

        self.db.commit()
