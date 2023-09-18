import chromadb
from langchain.docstore.document import Document
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from sqlalchemy.orm import Session

from app.constants import CHROMA_DIR, OPENAI_API_KEY
from app.db.models import EventORM
from app.db.schemas import EventInVectorDB


class Loader:
    def __init__(self, db: Session) -> None:
        self.db = db

        self.vectorstore = Chroma(
            client=chromadb.PersistentClient(path=CHROMA_DIR),
            embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY),
        )
        # self.vectorstore = PGVector(
        #     collection_name=COLLECTION_NAME,
        #     connection_string=CONNECTION_STRING,
        #     embedding_function=embeddings,
        # )

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
