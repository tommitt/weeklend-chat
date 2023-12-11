import uuid

from langchain.docstore.document import Document
from sqlalchemy.orm import Session

from app.constants import PINECONE_NAMESPACE, VECTORSTORE_TEXT_KEY
from app.db.models import EventORM
from app.db.schemas import EventInVectorstore
from app.utils.conn import get_pinecone_index, get_vectorstore


class Loader:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.pinecone_index = get_pinecone_index()
        self.vectorstore = get_vectorstore(index=self.pinecone_index)

    def add_document_sync(self, doc: Document) -> str:
        """
        Add a single document synchronously to the vectorstore.
        This implementation is vectorstore-specific: Pinecone.
        """
        doc_id = str(uuid.uuid4())
        doc_embedding = self.vectorstore.embeddings.embed_documents([doc.page_content])[
            0
        ]
        doc_metadata = doc.metadata
        doc_metadata[VECTORSTORE_TEXT_KEY] = doc.page_content

        _ = self.pinecone_index.upsert(
            vectors=[(doc_id, doc_embedding, doc_metadata)],
            namespace=PINECONE_NAMESPACE,
            async_req=False,
        )
        return doc_id

    def add_document_async(self, doc: Document) -> str:
        """
        Add a single document asynchronously to the vectorstore.
        This implementation is generic using Langchain interface.
        """
        doc_ids = self.vectorstore.add_documents([doc])
        return doc_ids[0]

    def vectorize_event(self, db_event: EventORM, async_add: bool = True) -> None:
        """Vectorize and add a single event to the vectorstore."""
        if db_event.is_vectorized:
            raise Exception(
                f"Can't vectorize event (id={db_event.id}) which is already vectorized."
            )

        event_doc = Document(
            page_content=db_event.description,
            metadata=EventInVectorstore.from_event_orm(db_event).__dict__,
        )

        if async_add:
            _ = self.add_document_async(event_doc)
        else:
            _ = self.add_document_sync(event_doc)

        db_event.is_vectorized = True
        self.db.commit()

    def get_not_vectorized_events(self) -> list[EventORM]:
        """Get non-vectorized events in the database."""
        query = self.db.query(EventORM).filter(EventORM.is_vectorized == False)
        return [e for e in query]

    def vectorize_events(self) -> None:
        """
        Vectorize all non-vectorized events in the database
        and add them to the vectorstore.
        """
        events = self.get_not_vectorized_events()
        if len(events) == 0:
            return

        for db_event in events:
            self.vectorize_event(db_event)
