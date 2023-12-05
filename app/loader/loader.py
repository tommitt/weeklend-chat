from langchain.docstore.document import Document
from sqlalchemy.orm import Session

from app.db.models import EventORM
from app.db.schemas import EventInVectorstore
from app.utils.conn import get_vectorstore


class Loader:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.vectorstore = get_vectorstore()
        self.events: list[EventORM] = []

    def vectorize_event(self, db_event: EventORM) -> None:
        event_doc = Document(
            page_content=db_event.description,
            metadata=EventInVectorstore.from_event_orm(db_event).__dict__,
        )
        self.vectorstore.add_documents([event_doc])
        db_event.is_vectorized = True
        self.db.commit()

    def get_not_vectorized_events(self) -> None:
        query = self.db.query(EventORM).filter(EventORM.is_vectorized == False)
        self.events = [e for e in query]

    def vectorize_events(self) -> None:
        for db_event in self.events:
            self.vectorize_event(db_event)
